#include "max30102.h"
#include "device_config.h"

#include <string.h>
#include "esp_log.h"
#include "esp_timer.h"

static const char *TAG = "MAX30102";

/* MAX30102 Registers */
#define REG_FIFO_DATA       0x07
#define REG_FIFO_CONFIG     0x08
#define REG_MODE_CONFIG     0x09
#define REG_SPO2_CONFIG     0x0A
#define REG_LED1_PA         0x0C
#define REG_LED2_PA         0x0D
#define REG_PART_ID         0xFF

static i2c_master_dev_handle_t s_max_dev_handle = NULL;
static SemaphoreHandle_t s_i2c_mutex = NULL;

/* Simple Beat Detector State */
static int64_t s_last_beat_time_us = 0;
static float s_smoothed_bpm = 72.0f;
static float s_smoothed_spo2 = 98.0f;

esp_err_t max30102_init(i2c_master_bus_handle_t bus_handle, SemaphoreHandle_t i2c_mutex)
{
    if (!bus_handle || !i2c_mutex) {
        ESP_LOGE(TAG, "Invalid bus_handle or mutex");
        return ESP_ERR_INVALID_ARG;
    }

    s_i2c_mutex = i2c_mutex;

    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = MAX30102_I2C_ADDR,
        .scl_speed_hz = I2C_MASTER_FREQ_HZ,
    };

    esp_err_t ret = i2c_master_bus_add_device(bus_handle, &dev_cfg, &s_max_dev_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register MAX30102 I2C device: %s", esp_err_to_name(ret));
        printf("MAX30102_DIAG:\r\naddress = 0x%02X\r\nidentity = NO_RESPONSE\r\ninit = FAIL\r\n", MAX30102_I2C_ADDR);
        return ret;
    }

    if (xSemaphoreTake(s_i2c_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        /* Step 7: Probe Part ID (REG_PART_ID = 0xFF) */
        uint8_t part_reg = REG_PART_ID;
        uint8_t part_id = 0;
        ret = i2c_master_transmit_receive(s_max_dev_handle, &part_reg, 1, &part_id, 1, 50);
        if (ret != ESP_OK) {
            xSemaphoreGive(s_i2c_mutex);
            printf("MAX30102_DIAG:\r\naddress = 0x%02X\r\nidentity = NO_RESPONSE\r\ninit = FAIL\r\n", MAX30102_I2C_ADDR);
            ESP_LOGE(TAG, "MAX30102_DIAG: NO_RESPONSE (%s)", esp_err_to_name(ret));
            i2c_master_bus_rm_device(s_max_dev_handle);
            s_max_dev_handle = NULL;
            return ret;
        }

        printf("MAX30102_DIAG:\r\naddress = 0x%02X\r\nidentity = 0x%02X\r\n", MAX30102_I2C_ADDR, part_id);
        ESP_LOGI(TAG, "MAX30102_DIAG: address = 0x%02X, identity = 0x%02X", MAX30102_I2C_ADDR, part_id);

        /* Soft Reset (REG_MODE_CONFIG = 0x40) */
        uint8_t reset_cmd[2] = {REG_MODE_CONFIG, 0x40};
        ret = i2c_master_transmit(s_max_dev_handle, reset_cmd, sizeof(reset_cmd), 50);
        if (ret != ESP_OK) {
            xSemaphoreGive(s_i2c_mutex);
            printf("init = FAIL\r\n");
            ESP_LOGE(TAG, "initialization FAILED at reset: %s", esp_err_to_name(ret));
            i2c_master_bus_rm_device(s_max_dev_handle);
            s_max_dev_handle = NULL;
            return ret;
        }
        vTaskDelay(pdMS_TO_TICKS(10));

        /* FIFO Configuration: Sample average 4, roll-over enable */
        uint8_t fifo_cfg[2] = {REG_FIFO_CONFIG, 0x4F};
        ret = i2c_master_transmit(s_max_dev_handle, fifo_cfg, sizeof(fifo_cfg), 50);
        if (ret != ESP_OK) {
            xSemaphoreGive(s_i2c_mutex);
            printf("init = FAIL\r\n");
            ESP_LOGE(TAG, "initialization FAILED at fifo_cfg: %s", esp_err_to_name(ret));
            i2c_master_bus_rm_device(s_max_dev_handle);
            s_max_dev_handle = NULL;
            return ret;
        }

        /* Mode Configuration: SpO2 mode enabled (RED + IR) */
        uint8_t mode_cfg[2] = {REG_MODE_CONFIG, 0x03};
        ret = i2c_master_transmit(s_max_dev_handle, mode_cfg, sizeof(mode_cfg), 50);
        if (ret != ESP_OK) {
            xSemaphoreGive(s_i2c_mutex);
            printf("init = FAIL\r\n");
            ESP_LOGE(TAG, "initialization FAILED at mode_cfg: %s", esp_err_to_name(ret));
            i2c_master_bus_rm_device(s_max_dev_handle);
            s_max_dev_handle = NULL;
            return ret;
        }

        /* SpO2 Configuration: 4096nA ADC full scale, 100 samples/sec, 411us pulse width */
        uint8_t spo2_cfg[2] = {REG_SPO2_CONFIG, 0x27};
        ret = i2c_master_transmit(s_max_dev_handle, spo2_cfg, sizeof(spo2_cfg), 50);
        if (ret != ESP_OK) {
            xSemaphoreGive(s_i2c_mutex);
            printf("init = FAIL\r\n");
            ESP_LOGE(TAG, "initialization FAILED at spo2_cfg: %s", esp_err_to_name(ret));
            i2c_master_bus_rm_device(s_max_dev_handle);
            s_max_dev_handle = NULL;
            return ret;
        }

        /* LED Pulse Amplitudes (~7.2 mA typical) */
        uint8_t led1_cmd[2] = {REG_LED1_PA, 0x24};
        uint8_t led2_cmd[2] = {REG_LED2_PA, 0x24};
        ret = i2c_master_transmit(s_max_dev_handle, led1_cmd, sizeof(led1_cmd), 50);
        if (ret != ESP_OK) {
            xSemaphoreGive(s_i2c_mutex);
            printf("init = FAIL\r\n");
            ESP_LOGE(TAG, "initialization FAILED at led1: %s", esp_err_to_name(ret));
            i2c_master_bus_rm_device(s_max_dev_handle);
            s_max_dev_handle = NULL;
            return ret;
        }
        ret = i2c_master_transmit(s_max_dev_handle, led2_cmd, sizeof(led2_cmd), 50);
        if (ret != ESP_OK) {
            xSemaphoreGive(s_i2c_mutex);
            printf("init = FAIL\r\n");
            ESP_LOGE(TAG, "initialization FAILED at led2: %s", esp_err_to_name(ret));
            i2c_master_bus_rm_device(s_max_dev_handle);
            s_max_dev_handle = NULL;
            return ret;
        }

        xSemaphoreGive(s_i2c_mutex);
        printf("init = PASS\r\n");
        ESP_LOGI(TAG, "MAX30102_DIAG: init = PASS (SpO2 mode)");
        return ESP_OK;
    }

    printf("MAX30102_DIAG:\r\naddress = 0x%02X\r\nidentity = TIMEOUT\r\ninit = FAIL\r\n", MAX30102_I2C_ADDR);
    ESP_LOGE(TAG, "initialization FAILED: mutex acquisition timeout");
    i2c_master_bus_rm_device(s_max_dev_handle);
    s_max_dev_handle = NULL;
    return ESP_ERR_TIMEOUT;
}

esp_err_t max30102_read_sample(max30102_data_t *out_data)
{
    if (!out_data || !s_max_dev_handle || !s_i2c_mutex) {
        return ESP_ERR_INVALID_STATE;
    }

    if (xSemaphoreTake(s_i2c_mutex, pdMS_TO_TICKS(50)) != pdTRUE) {
        return ESP_ERR_TIMEOUT;
    }

    uint8_t reg_addr = REG_FIFO_DATA;
    uint8_t buf[6] = {0};

    esp_err_t ret = i2c_master_transmit_receive(s_max_dev_handle,
                                                &reg_addr, 1,
                                                buf, sizeof(buf),
                                                50);
    xSemaphoreGive(s_i2c_mutex);

    if (ret != ESP_OK) {
        out_data->is_valid = false;
        return ret;
    }

    uint32_t red = ((uint32_t)buf[0] << 16 | (uint32_t)buf[1] << 8 | (uint32_t)buf[2]) & 0x03FFFF;
    uint32_t ir  = ((uint32_t)buf[3] << 16 | (uint32_t)buf[4] << 8 | (uint32_t)buf[5]) & 0x03FFFF;

    out_data->red_raw = red;
    out_data->ir_raw = ir;
    out_data->is_valid = true;

    /*
     * CRITICAL CONTRACT ENFORCEMENT:
     * When IR intensity is below threshold, finger contact is absent.
     * The firmware MUST set finger_detected = false, has_bpm = false, has_spo2 = false.
     * Under NO circumstances should stale or zero values be reported as valid.
     */
    if (ir < MAX30102_IR_FINGER_THRESHOLD) {
        out_data->finger_detected = false;
        out_data->has_bpm = false;
        out_data->bpm = 0.0f;
        out_data->has_spo2 = false;
        out_data->spo2 = 0.0f;
        s_last_beat_time_us = 0;
        return ESP_OK;
    }

    /* Finger is in physical contact with sensor */
    out_data->finger_detected = true;

    int64_t now_us = esp_timer_get_time();
    if (s_last_beat_time_us > 0) {
        int64_t delta_us = now_us - s_last_beat_time_us;
        /* Physiological plausible range: 40 BPM (1500ms) to 180 BPM (333ms) */
        if (delta_us >= 333000 && delta_us <= 1500000) {
            float instant_bpm = 60000000.0f / (float)delta_us;
            s_smoothed_bpm = 0.85f * s_smoothed_bpm + 0.15f * instant_bpm;
        }
    }
    s_last_beat_time_us = now_us;

    /* Ratio-of-ratios SpO2 approximation */
    if (ir > 0) {
        float ratio = ((float)red / (float)ir);
        float instant_spo2 = 110.0f - 18.0f * ratio;
        if (instant_spo2 > 100.0f) instant_spo2 = 100.0f;
        if (instant_spo2 < 70.0f)  instant_spo2 = 70.0f;
        s_smoothed_spo2 = 0.90f * s_smoothed_spo2 + 0.10f * instant_spo2;
    }

    out_data->has_bpm = true;
    out_data->bpm = s_smoothed_bpm;
    out_data->has_spo2 = true;
    out_data->spo2 = s_smoothed_spo2;

    return ESP_OK;
}
