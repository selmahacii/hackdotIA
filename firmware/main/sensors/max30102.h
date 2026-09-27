#ifndef MAX30102_H
#define MAX30102_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "driver/i2c_master.h"

typedef struct {
    bool finger_detected;
    bool has_bpm;
    float bpm;
    bool has_spo2;
    float spo2;
    uint32_t ir_raw;
    uint32_t red_raw;
    bool is_valid;
} max30102_data_t;

/**
 * Initializes the MAX30102 photoplethysmography sensor at address 0x57.
 * Configures FIFO, SpO2 mode, LED pulse amplitude, and sample rate.
 *
 * @param bus_handle Initialized I2C master bus handle
 * @param i2c_mutex FreeRTOS mutex protecting shared I2C bus
 */
esp_err_t max30102_init(i2c_master_bus_handle_t bus_handle, SemaphoreHandle_t i2c_mutex);

/**
 * Reads sensor FIFO, updates raw IR/RED levels, and computes physiological estimates.
 * Enforces contract rule: if finger_detected is false, has_bpm and has_spo2 are false.
 *
 * @param out_data Pointer to max30102_data_t
 */
esp_err_t max30102_read_sample(max30102_data_t *out_data);

#endif /* MAX30102_H */
