#ifndef DEVICE_CONFIG_H
#define DEVICE_CONFIG_H

#include <stdint.h>
#include <stdbool.h>

/* =========================================================================
 * HARDWARE PIN DEFINITIONS (ESP32 DevKit / Custom Bracelet)
 * ========================================================================= */
#define PIN_I2C_SDA             21
#define PIN_I2C_SCL             22
#define I2C_MASTER_FREQ_HZ      100000  /* 100 kHz Standard Mode for stability */

#define PIN_GPS_TX              17      /* ESP32 TX -> GPS RX */
#define PIN_GPS_RX              16      /* ESP32 RX <- GPS TX */
#define GPS_UART_PORT           2
#define GPS_BAUD_RATE           9600

#define PIN_DHT11               4

#define PIN_BUZZER              25
#define PIN_LED_GREEN           26      /* System & Network status */
#define PIN_LED_RED             27      /* Hardware Warning indicator */

/* Temporary diagnostic flags */
#define HARDWARE_DIAGNOSTIC_MODE      1
#define BUZZER_BOOT_BEEP              0
#define CONFIG_DIAGNOSTIC_BOOT_SILENT 1

/* =========================================================================
 * SENSOR I2C ADDRESSES & CONFIGURATIONS
 * ========================================================================= */
#define MPU6050_I2C_ADDR        0x68
#define MAX30102_I2C_ADDR       0x57

/* MPU6050 Sensitivity for +-8g */
#define MPU6050_ACCEL_CONFIG_8G 0x10    /* FS_SEL = 2 (+-8g) */
#define MPU6050_SENSITIVITY_8G  4096.0f /* LSB / g */

/* MAX30102 Detection Parameters */
#define MAX30102_IR_FINGER_THRESHOLD  50000UL  /* Configurable IR threshold for finger detection */

/* DHT11 Timing */
#define DHT11_MIN_READ_INTERVAL_MS    2000     /* Physical minimum 2s between reads */

/* =========================================================================
 * NETWORK & PROTOCOL DEFAULTS
 * (May be overridden via Kconfig / sdkconfig)
 * ========================================================================= */
#ifndef CONFIG_DEVICE_UID
#define CONFIG_DEVICE_UID       "ESP32-ELDERLY-001"
#endif

#ifndef CONFIG_WIFI_SSID
#define CONFIG_WIFI_SSID        "SmartElderly_AP"
#endif

#ifndef CONFIG_WIFI_PASSWORD
#define CONFIG_WIFI_PASSWORD    "change_me_in_sdkconfig"
#endif

#ifndef CONFIG_MQTT_BROKER_URI
#define CONFIG_MQTT_BROKER_URI  "mqtt://192.168.1.100:1883"
#endif

#define MQTT_TOPIC_PREFIX       "elderly/"
#define MQTT_TELEMETRY_SUFFIX   "/telemetry"
#define MQTT_QOS_LEVEL          1

/* Telemetry loop publication interval */
#define TELEMETRY_INTERVAL_MS   1000    /* 1 message per second (1 Hz) */

/* NTP Configuration */
#define NTP_SERVER_NAME         "pool.ntp.org"
#define NTP_SYNC_TIMEOUT_MS     15000

#endif /* DEVICE_CONFIG_H */
