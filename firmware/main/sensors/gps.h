#ifndef GPS_H
#define GPS_H

#include <stdbool.h>
#include "esp_err.h"

typedef struct {
    bool gps_fix_valid;
    bool has_coordinates;
    float latitude;
    float longitude;
} gps_data_t;

/**
 * Initializes UART2 for GPS receiver (RX=GPIO16, TX=GPIO17, 9600 baud).
 */
esp_err_t gps_init(void);

/**
 * Parses raw NMEA sentence ($GPRMC / $GNRMC).
 * Validates checksum, fix status ('A' vs 'V'), and decodes decimal coordinates.
 *
 * @param nmea_sentence Null-terminated NMEA string
 * @param out_data Pointer to gps_data_t to update
 * @return true if valid RMC was parsed, false otherwise
 */
bool gps_parse_rmc(const char *nmea_sentence, gps_data_t *out_data);

/**
 * Thread-safe retrieval of latest GPS snapshot.
 *
 * @param out_data Pointer to gps_data_t
 */
void gps_get_latest_data(gps_data_t *out_data);

/**
 * Background FreeRTOS task reading UART2 and feeding the parser.
 */
void gps_task(void *pvParameters);

#endif /* GPS_H */
