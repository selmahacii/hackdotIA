#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <stdbool.h>
#include <stdint.h>
#include "sensors/mpu6050.h"
#include "sensors/max30102.h"
#include "sensors/dht11.h"
#include "sensors/gps.h"

typedef struct {
    char event_id[37];
    char device_uid[64];
    char timestamp[25];

    /* MAX30102 PPG */
    max30102_data_t max30102;

    /* DHT11 Environmental */
    dht11_data_t dht11;

    /* MPU6050 Kinematics */
    mpu6050_data_t mpu6050;

    /* GPS Positioning */
    gps_data_t gps;

    /* Device Telemetry */
    bool has_battery;
    int battery_level;

    bool has_wifi_rssi;
    int wifi_rssi;
} telemetry_snapshot_t;

/**
 * Serializes a telemetry snapshot into a JSON string strictly compliant with
 * the backend Pydantic SensorTelemetryPayload schema.
 *
 * Caller is responsible for freeing the returned string using free().
 *
 * @param snapshot Pointer to populated telemetry snapshot
 * @return Allocated JSON string or NULL on failure
 */
char *telemetry_serialize_json(const telemetry_snapshot_t *snapshot);

/**
 * Returns battery level if hardware ADC is available.
 * If no hardware ADC is configured, sets *has_battery = false.
 */
int battery_get_level(bool *has_battery);

#endif /* TELEMETRY_H */
