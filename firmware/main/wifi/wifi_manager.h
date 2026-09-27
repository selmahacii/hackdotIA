#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

typedef enum {
    WIFI_STATE_DISCONNECTED = 0,
    WIFI_STATE_CONNECTING,
    WIFI_STATE_CONNECTED
} wifi_state_t;

/**
 * Initializes Wi-Fi in Station mode using credentials from device_config.h / sdkconfig.
 */
esp_err_t wifi_manager_init(void);

/**
 * Checks whether the device is currently connected and has an assigned IP address.
 */
bool wifi_manager_is_connected(void);

/**
 * Retrieves current Wi-Fi RSSI in dBm.
 * Returns true if connected and RSSI valid, false otherwise.
 */
bool wifi_manager_get_rssi(int *out_rssi);

#endif /* WIFI_MANAGER_H */
