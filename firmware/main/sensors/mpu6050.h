#ifndef MPU6050_H
#define MPU6050_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "driver/i2c_master.h"

typedef struct {
    float accel_x_g;
    float accel_y_g;
    float accel_z_g;
    float accel_magnitude_g;
    bool is_valid;
} mpu6050_data_t;

/**
 * Initializes the MPU6050 sensor on the I2C master bus at 0x68.
 * Configures full-scale range to +-8g (sensitivity: 4096 LSB/g).
 *
 * @param bus_handle Initialized I2C master bus handle
 * @param i2c_mutex FreeRTOS mutex protecting shared I2C bus transactions
 */
esp_err_t mpu6050_init(i2c_master_bus_handle_t bus_handle, SemaphoreHandle_t i2c_mutex);

/**
 * Reads 3-axis acceleration and computes vector magnitude in g.
 * Protected by shared I2C mutex.
 *
 * @param out_data Pointer to mpu6050_data_t to store converted g values
 */
esp_err_t mpu6050_read_acceleration(mpu6050_data_t *out_data);

#endif /* MPU6050_H */
