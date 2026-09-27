#include "mpu6050.h"
#include "device_config.h"

#include <math.h>
#include "esp_log.h"

static const char *TAG = "MPU6050";

/* MPU6050 Register Map */
#define REG_ACCEL_CONFIG    0x1C
#define REG_ACCEL_XOUT_H    0x3B
#define REG_PWR_MGMT_1      0x6B

static i2c_master_dev_handle_t s_mpu_dev_handle = NULL;
static SemaphoreHandle_t s_i2c_mutex = NULL;

esp_err_t mpu6050_init(i2c_master_bus_handle_t bus_handle, SemaphoreHandle_t i2c_mutex)
{
    if (!bus_handle || !i2c_mutex) {
        ESP_LOGE(TAG, "Invalid bus_handle or mutex pointer");
        return ESP_ERR_INVALID_ARG;
    }

    s_i2c_mutex = i2c_mutex;

    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = MPU6050_I2C_ADDR,
        .scl_speed_hz = I2C_MASTER_FREQ_HZ,
    };

    esp_err_t ret = i2c_master_bus_add_device(bus_handle, &dev_cfg, &s_mpu_dev_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to add MPU6050 device to I2C bus: %s", esp_err_to_name(ret));
        return ret;
    }

    if (xSemaphoreTake(s_i2c_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        /* 1. Wake up device from default sleep mode (PWR_MGMT_1 = 0x00) */
        uint8_t pwr_cmd[2] = {REG_PWR_MGMT_1, 0x00};
        ret = i2c_master_transmit(s_mpu_dev_handle, pwr_cmd, sizeof(pwr_cmd), 100);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "initialization FAILED at wake: %s", esp_err_to_name(ret));
            xSemaphoreGive(s_i2c_mutex);
            return ret;
        }

        /* 2. Configure +-8g full scale range (ACCEL_CONFIG = 0x10) */
        uint8_t accel_cfg_cmd[2] = {REG_ACCEL_CONFIG, MPU6050_ACCEL_CONFIG_8G};
        ret = i2c_master_transmit(s_mpu_dev_handle, accel_cfg_cmd, sizeof(accel_cfg_cmd), 100);
        xSemaphoreGive(s_i2c_mutex);

        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "initialization FAILED at scale: %s", esp_err_to_name(ret));
            return ret;
        }

        ESP_LOGI(TAG, "initialization SUCCESS (+-8g mode, 4096 LSB/g)");
        return ESP_OK;
    }

    ESP_LOGE(TAG, "initialization FAILED: mutex acquisition timeout");
    return ESP_ERR_TIMEOUT;
}

esp_err_t mpu6050_read_acceleration(mpu6050_data_t *out_data)
{
    if (!out_data || !s_mpu_dev_handle || !s_i2c_mutex) {
        return ESP_ERR_INVALID_STATE;
    }

    if (xSemaphoreTake(s_i2c_mutex, pdMS_TO_TICKS(50)) != pdTRUE) {
        return ESP_ERR_TIMEOUT;
    }

    uint8_t reg_addr = REG_ACCEL_XOUT_H;
    uint8_t buffer[6] = {0};

    esp_err_t ret = i2c_master_transmit_receive(s_mpu_dev_handle,
                                                &reg_addr, 1,
                                                buffer, sizeof(buffer),
                                                50);
    xSemaphoreGive(s_i2c_mutex);

    if (ret != ESP_OK) {
        out_data->is_valid = false;
        return ret;
    }

    int16_t raw_x = (int16_t)((buffer[0] << 8) | buffer[1]);
    int16_t raw_y = (int16_t)((buffer[2] << 8) | buffer[3]);
    int16_t raw_z = (int16_t)((buffer[4] << 8) | buffer[5]);

    /* Convert to units of g using 4096 LSB/g (+-8g full scale) */
    out_data->accel_x_g = (float)raw_x / MPU6050_SENSITIVITY_8G;
    out_data->accel_y_g = (float)raw_y / MPU6050_SENSITIVITY_8G;
    out_data->accel_z_g = (float)raw_z / MPU6050_SENSITIVITY_8G;

    out_data->accel_magnitude_g = sqrtf(out_data->accel_x_g * out_data->accel_x_g +
                                        out_data->accel_y_g * out_data->accel_y_g +
                                        out_data->accel_z_g * out_data->accel_z_g);
    out_data->is_valid = true;

    return ESP_OK;
}
