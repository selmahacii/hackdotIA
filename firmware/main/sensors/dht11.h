#ifndef DHT11_H
#define DHT11_H

#include <stdbool.h>
#include "esp_err.h"

typedef struct {
    float temperature_c;
    float humidity_percent;
    bool is_valid;
} dht11_data_t;

/**
 * Initializes the GPIO pin for the DHT11 single-wire interface.
 */
esp_err_t dht11_init(void);

/**
 * Reads ambient temperature (°C) and relative humidity (%) from DHT11.
 * Enforces a minimum 2-second physical sampling interval.
 *
 * @param out_data Pointer to dht11_data_t
 */
esp_err_t dht11_read(dht11_data_t *out_data);

#endif /* DHT11_H */
