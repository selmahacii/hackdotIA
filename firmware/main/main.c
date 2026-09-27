#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "nvs_flash.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"

#include "system/device_config.h"
#include "system/time_sync.h"
#include "sensors/mpu6050.h"
#include "sensors/max30102.h"
#include "sensors/dht11.h"
#include "sensors/gps.h"
#include "telemetry/telemetry.h"
#include "wifi/wifi_manager.h"
#include "mqtt/app_mqtt.h"
#include "esp_system.h"

static const char *TAG = "SMART_ELDERLY_MAIN";

/* FreeRTOS Mutexes protecting shared resources */
static SemaphoreHandle_t s_i2c_bus_mutex = NULL;
static SemaphoreHandle_t s_sensor_snapshot_mutex = NULL;

/* Sensor availability flags to avoid I2C bombardment when hardware fails */
static bool s_mpu6050_available = false;
static bool s_max30102_available = false;

/* Latest coherent sensor data snapshot */
static telemetry_snapshot_t s_latest_snapshot;

/* Pending message buffer for idempotent MQTT retry */
static char *s_pending_retry_payload = NULL;

static void init_actuators(void)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << PIN_BUZZER) | (1ULL << PIN_LED_GREEN) | (1ULL << PIN_LED_RED),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);

#ifndef CONFIG_DIAGNOSTIC_BOOT_SILENT
    /* Single short confirmation beep on boot (50ms) */
    gpio_set_level(PIN_BUZZER, 1);
    vTaskDelay(pdMS_TO_TICKS(50));
    gpio_set_level(PIN_BUZZER, 0);
#else
    ESP_LOGI("BOOT", "Buzzer silent mode active (CONFIG_DIAGNOSTIC_BOOT_SILENT)");
#endif

    gpio_set_level(PIN_LED_GREEN, 0);
    gpio_set_level(PIN_LED_RED, 0);
}

/**
 * High-frequency sensor sampling task (25 Hz):
 * Reads MPU6050 and MAX30102 through the shared I2C bus mutex.
 */
static void sensor_sampling_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Sensor acquisition task started (25 Hz)");
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(40); /* 40ms = 25 Hz */

    while (1) {
        mpu6050_data_t mpu_val = {0};
        max30102_data_t max_val = {0};

        /* Read MPU6050 if available */
        if (s_mpu6050_available) {
            mpu6050_read_acceleration(&mpu_val);
        } else {
            mpu_val.is_valid = false;
        }

        /* Read MAX30102 if available */
        if (s_max30102_available) {
            max30102_read_sample(&max_val);
        } else {
            max_val.is_valid = false;
            max_val.finger_detected = false;
            max_val.has_bpm = false;
            max_val.has_spo2 = false;
        }

        /* Update coherent snapshot */
        if (xSemaphoreTake(s_sensor_snapshot_mutex, pdMS_TO_TICKS(20)) == pdTRUE) {
            s_latest_snapshot.mpu6050 = mpu_val;
            s_latest_snapshot.max30102 = max_val;
            xSemaphoreGive(s_sensor_snapshot_mutex);
        }

        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

/**
 * Environmental sensor task (0.5 Hz):
 * Reads DHT11 respecting its 2-second physical interval.
 */
static void dht11_task(void *pvParameters)
{
    ESP_LOGI(TAG, "DHT11 acquisition task started (0.5 Hz)");

    while (1) {
        dht11_data_t dht_val = {0};
        dht11_read(&dht_val);

        if (xSemaphoreTake(s_sensor_snapshot_mutex, pdMS_TO_TICKS(50)) == pdTRUE) {
            s_latest_snapshot.dht11 = dht_val;
            xSemaphoreGive(s_sensor_snapshot_mutex);
        }

        vTaskDelay(pdMS_TO_TICKS(DHT11_MIN_READ_INTERVAL_MS));
    }
}

/**
 * Status LED feedback task:
 * Decoupled from medical alarms. Provides device-level diagnostic feedback only.
 */
static void status_led_task(void *pvParameters)
{
    while (1) {
        bool wifi_ok = wifi_manager_is_connected();
        bool mqtt_ok = mqtt_app_is_connected();
        bool time_ok = time_sync_is_synced();

        if (wifi_ok && mqtt_ok && time_ok) {
            /* Nominal: Green LED solid ON */
            gpio_set_level(PIN_LED_GREEN, 1);
            gpio_set_level(PIN_LED_RED, 0);
            vTaskDelay(pdMS_TO_TICKS(1000));
        } else {
            /* Connecting or degraded: Green LED blinking */
            gpio_set_level(PIN_LED_GREEN, 1);
            vTaskDelay(pdMS_TO_TICKS(200));
            gpio_set_level(PIN_LED_GREEN, 0);
            vTaskDelay(pdMS_TO_TICKS(200));

            /* If NTP not synced or network down, pulse Red LED */
            if (!time_ok || !wifi_ok) {
                gpio_set_level(PIN_LED_RED, 1);
                vTaskDelay(pdMS_TO_TICKS(100));
                gpio_set_level(PIN_LED_RED, 0);
            }
        }
    }
}

/**
 * Official Telemetry Publisher Task (1 Hz):
 * Takes coherent atomic snapshot, constructs JSON matching backend contract exactly,
 * manages NTP clock validity, and guarantees idempotent retries upon MQTT publish failure.
 */
static void telemetry_publisher_task(void *pvParameters)
{
    ESP_LOGI(TAG, "Telemetry publisher task started (1 Hz)");
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(TELEMETRY_INTERVAL_MS);

    while (1) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /*
         * 1. NTP Synchronization Check:
         * Never emit un-synchronized timestamps (1970 epoch) into backend telemetry.
         */
        if (!time_sync_is_synced()) {
            ESP_LOGW(TAG, "Telemetry paused: Device clock not yet synchronized with NTP (TIME_NOT_SYNCED)");
            continue;
        }

        if (!mqtt_app_is_connected()) {
            ESP_LOGD(TAG, "MQTT not connected, skipping publish cycle");
            continue;
        }

        /*
         * 2. Idempotent Retry Logic:
         * If a previous publish failed, re-attempt with the EXACT SAME payload and event_id.
         */
        if (s_pending_retry_payload != NULL) {
            ESP_LOGW(TAG, "Retrying previous failed telemetry publish (maintaining same event_id)");
            bool retry_ok = mqtt_app_publish_telemetry(s_pending_retry_payload);
            if (retry_ok) {
                free(s_pending_retry_payload);
                s_pending_retry_payload = NULL;
                ESP_LOGI(TAG, "Pending telemetry retry succeeded");
            }
            continue;
        }

        /*
         * 3. Fresh Telemetry Measurement Cycle:
         * Generate a single unique UUID v4 event_id for this measurement.
         */
        telemetry_snapshot_t snapshot;
        memset(&snapshot, 0, sizeof(snapshot));

        time_sync_generate_uuid_v4(snapshot.event_id, sizeof(snapshot.event_id));
        strncpy(snapshot.device_uid, CONFIG_DEVICE_UID, sizeof(snapshot.device_uid) - 1);
        time_sync_get_iso8601(snapshot.timestamp, sizeof(snapshot.timestamp));

        /* Capture atomic sensor data */
        if (xSemaphoreTake(s_sensor_snapshot_mutex, pdMS_TO_TICKS(50)) == pdTRUE) {
            snapshot.mpu6050 = s_latest_snapshot.mpu6050;
            snapshot.max30102 = s_latest_snapshot.max30102;
            snapshot.dht11 = s_latest_snapshot.dht11;
            xSemaphoreGive(s_sensor_snapshot_mutex);
        }

        /* Capture GPS data */
        gps_get_latest_data(&snapshot.gps);

        /* Capture Battery & RSSI */
        snapshot.battery_level = battery_get_level(&snapshot.has_battery);
        snapshot.has_wifi_rssi = wifi_manager_get_rssi(&snapshot.wifi_rssi);

        /*
         * 4. Strict Backend JSON Serialization
         */
        char *json_str = telemetry_serialize_json(&snapshot);
        if (!json_str) {
            ESP_LOGE(TAG, "Failed to serialize telemetry JSON");
            continue;
        }

        /*
         * 5. MQTT QoS 1 Publication
         */
        bool pub_ok = mqtt_app_publish_telemetry(json_str);
        if (!pub_ok) {
            /* Store for retry next second with identical event_id */
            s_pending_retry_payload = json_str;
            ESP_LOGW(TAG, "MQTT publish failed, enqueued for retry with event_id='%s'", snapshot.event_id);
        } else {
            free(json_str);
        }
    }
}

void app_main(void)
{
    /* 0. Boot Marker & Reset Reason Diagnostic */
    esp_reset_reason_t rst_reason = esp_reset_reason();
    ESP_LOGI("BOOT", "=== BOOT SEQUENCE START ===");
    ESP_LOGI("BOOT", "Reset Reason: %d (%s)", (int)rst_reason,
             (rst_reason == ESP_RST_BROWNOUT) ? "ESP_RST_BROWNOUT: Brownout Detector was triggered!" :
             (rst_reason == ESP_RST_POWERON) ? "ESP_RST_POWERON: Normal power on" :
             (rst_reason == ESP_RST_SW) ? "ESP_RST_SW: Software reset" : "OTHER");
    ESP_LOGI("BOOT", "Device UID: %s | Target: ESP32", CONFIG_DEVICE_UID);

    /* 1. Initialize NVS Flash */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    /* 2. Initialize Actuators & Indicators */
    init_actuators();

    /* 3. Initialize Shared Synchronization Mutexes */
    s_i2c_bus_mutex = xSemaphoreCreateMutex();
    s_sensor_snapshot_mutex = xSemaphoreCreateMutex();

    /* 4. Initialize I2C Master Bus (driver/i2c_master.h) */
    i2c_master_bus_config_t i2c_bus_config = {
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .i2c_port = 0,
        .scl_io_num = PIN_I2C_SCL,
        .sda_io_num = PIN_I2C_SDA,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    i2c_master_bus_handle_t bus_handle = NULL;
    ESP_ERROR_CHECK(i2c_new_master_bus(&i2c_bus_config, &bus_handle));

    /* =========================================================================
     * I2C DIAGNOSTIC: Check line levels & perform bus scan
     * ========================================================================= */
    int sda_lvl = gpio_get_level(PIN_I2C_SDA);
    int scl_lvl = gpio_get_level(PIN_I2C_SCL);
    ESP_LOGI("I2C_DIAG", "SDA=%d SCL=%d", sda_lvl, scl_lvl);

    ESP_LOGI("I2C_DIAG", "Starting I2C scan...");
    int devices_found = 0;
    for (uint16_t addr = 0x01; addr < 0x80; addr++) {
        esp_err_t probe_res = i2c_master_probe(bus_handle, addr, 20);
        if (probe_res == ESP_OK) {
            ESP_LOGI("I2C_DIAG", "Device ACK at 0x%02X", addr);
            devices_found++;
        }
    }
    if (devices_found > 0) {
        ESP_LOGI("I2C_DIAG", "Scan complete, %d device(s) found", devices_found);
    } else {
        ESP_LOGI("I2C_DIAG", "Scan complete, NO devices found");
    }

    /* =========================================================================
     * 5. SENSOR INIT: Check return codes and log explicitly
     * ========================================================================= */
    ESP_LOGI("SENSOR_INIT", "=== INITIALIZING HARDWARE SENSORS ===");
    esp_err_t mpu_ret = mpu6050_init(bus_handle, s_i2c_bus_mutex);
    if (mpu_ret == ESP_OK) {
        s_mpu6050_available = true;
        ESP_LOGI("SENSOR_INIT", "MPU6050: initialization SUCCESS");
    } else {
        s_mpu6050_available = false;
        ESP_LOGE("SENSOR_INIT", "MPU6050: initialization FAILED: %s", esp_err_to_name(mpu_ret));
    }

    esp_err_t max_ret = max30102_init(bus_handle, s_i2c_bus_mutex);
    if (max_ret == ESP_OK) {
        s_max30102_available = true;
        ESP_LOGI("SENSOR_INIT", "MAX30102: initialization SUCCESS");
    } else {
        s_max30102_available = false;
        ESP_LOGE("SENSOR_INIT", "MAX30102: initialization FAILED: %s", esp_err_to_name(max_ret));
    }

    dht11_init();
    gps_init();

    /* =========================================================================
     * 6. Defer Wi-Fi start by 5 seconds to isolate Brownout origin
     * ========================================================================= */
    ESP_LOGI("I2C_DIAG", "Hardware diagnostic delay active");
    vTaskDelay(pdMS_TO_TICKS(5000));
    ESP_LOGI("I2C_DIAG", "Starting Wi-Fi after diagnostic delay");

    ESP_LOGI("WIFI_START", "=== STARTING WI-FI SUBSYSTEM ===");
    wifi_manager_init();
    mqtt_app_start();

    /* 7. Launch FreeRTOS Tasks */
    xTaskCreatePinnedToCore(gps_task, "gps_task", 4096, NULL, 3, NULL, 1);
    xTaskCreatePinnedToCore(sensor_sampling_task, "sensor_task", 4096, NULL, 4, NULL, 1);
    xTaskCreatePinnedToCore(dht11_task, "dht11_task", 3072, NULL, 2, NULL, 1);
    xTaskCreatePinnedToCore(status_led_task, "status_led_task", 2048, NULL, 1, NULL, 0);
    xTaskCreatePinnedToCore(telemetry_publisher_task, "telemetry_task", 6144, NULL, 5, NULL, 0);

    ESP_LOGI(TAG, "All FreeRTOS tasks started successfully");
}
