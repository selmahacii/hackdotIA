#include "telemetry.h"
#include "cJSON.h"
#include <stdlib.h>
#include <string.h>

char *telemetry_serialize_json(const telemetry_snapshot_t *snapshot)
{
    if (!snapshot) {
        return NULL;
    }

    cJSON *root = cJSON_CreateObject();
    if (!root) {
        return NULL;
    }

    /* Core metadata */
    cJSON_AddStringToObject(root, "schema_version", "1.0");
    cJSON_AddStringToObject(root, "event_id", snapshot->event_id);
    cJSON_AddStringToObject(root, "device_uid", snapshot->device_uid);
    cJSON_AddStringToObject(root, "timestamp", snapshot->timestamp);

    /*
     * MAX30102 PPG Sensor:
     * Cross-contract enforcement:
     * If finger_detected == false -> bpm must be null, spo2 must be null.
     */
    cJSON_AddBoolToObject(root, "finger_detected", snapshot->max30102.finger_detected);

    if (snapshot->max30102.finger_detected && snapshot->max30102.has_bpm) {
        cJSON_AddNumberToObject(root, "bpm", snapshot->max30102.bpm);
    } else {
        cJSON_AddNullToObject(root, "bpm");
    }

    if (snapshot->max30102.finger_detected && snapshot->max30102.has_spo2) {
        cJSON_AddNumberToObject(root, "spo2", snapshot->max30102.spo2);
    } else {
        cJSON_AddNullToObject(root, "spo2");
    }

    /*
     * DHT11 Environmental Sensor:
     * Strict keys matching backend: temperature_c, humidity_percent.
     */
    if (snapshot->dht11.is_valid) {
        cJSON_AddNumberToObject(root, "temperature_c", snapshot->dht11.temperature_c);
        cJSON_AddNumberToObject(root, "humidity_percent", snapshot->dht11.humidity_percent);
    } else {
        cJSON_AddNullToObject(root, "temperature_c");
        cJSON_AddNullToObject(root, "humidity_percent");
    }

    /*
     * MPU6050 Kinematics:
     * Strict keys matching backend: accel_x_g, accel_y_g, accel_z_g, accel_magnitude_g.
     */
    if (snapshot->mpu6050.is_valid) {
        cJSON_AddNumberToObject(root, "accel_x_g", snapshot->mpu6050.accel_x_g);
        cJSON_AddNumberToObject(root, "accel_y_g", snapshot->mpu6050.accel_y_g);
        cJSON_AddNumberToObject(root, "accel_z_g", snapshot->mpu6050.accel_z_g);
        cJSON_AddNumberToObject(root, "accel_magnitude_g", snapshot->mpu6050.accel_magnitude_g);
    } else {
        cJSON_AddNullToObject(root, "accel_x_g");
        cJSON_AddNullToObject(root, "accel_y_g");
        cJSON_AddNullToObject(root, "accel_z_g");
        cJSON_AddNullToObject(root, "accel_magnitude_g");
    }

    /*
     * GPS Positioning:
     * Cross-contract enforcement:
     * If gps_fix_valid == false -> gps_latitude and gps_longitude must be null (never 0.0).
     */
    cJSON_AddBoolToObject(root, "gps_fix_valid", snapshot->gps.gps_fix_valid);

    if (snapshot->gps.gps_fix_valid && snapshot->gps.has_coordinates) {
        cJSON_AddNumberToObject(root, "gps_latitude", snapshot->gps.latitude);
        cJSON_AddNumberToObject(root, "gps_longitude", snapshot->gps.longitude);
    } else {
        cJSON_AddNullToObject(root, "gps_latitude");
        cJSON_AddNullToObject(root, "gps_longitude");
    }

    /* Hardware & Connectivity Telemetry */
    if (snapshot->has_battery) {
        cJSON_AddNumberToObject(root, "battery_level", snapshot->battery_level);
    } else {
        cJSON_AddNullToObject(root, "battery_level");
    }

    if (snapshot->has_wifi_rssi) {
        cJSON_AddNumberToObject(root, "wifi_rssi", snapshot->wifi_rssi);
    } else {
        cJSON_AddNullToObject(root, "wifi_rssi");
    }

    char *json_str = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);

    return json_str;
}

int battery_get_level(bool *has_battery)
{
    if (has_battery) {
        /*
         * Real hardware abstraction:
         * If ADC hardware voltage divider is connected, measure ADC and return level.
         * Default: not wired on current bench, report unavailable/null to prevent fake 89%.
         */
        *has_battery = false;
    }
    return 0;
}
