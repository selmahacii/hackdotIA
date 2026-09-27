#ifndef APP_MQTT_H
#define APP_MQTT_H

#include <stdbool.h>
#include "esp_err.h"

typedef enum {
    MQTT_STATE_DISCONNECTED = 0,
    MQTT_STATE_CONNECTING,
    MQTT_STATE_CONNECTED
} mqtt_state_t;

/**
 * Initializes the esp-mqtt client connected to CONFIG_MQTT_BROKER_URI.
 */
esp_err_t mqtt_app_start(void);

/**
 * Checks whether the MQTT client is currently connected and active with the broker.
 */
bool mqtt_app_is_connected(void);

/**
 * Publishes a telemetry JSON payload to topic 'elderly/{device_uid}/telemetry' at QoS 1.
 * Returns true if enqueued/sent successfully, false on network failure.
 *
 * @param json_payload Null-terminated JSON string
 * @return true on success, false if publish failed (triggering retry of the SAME event_id)
 */
bool mqtt_app_publish_telemetry(const char *json_payload);

#endif /* APP_MQTT_H */
