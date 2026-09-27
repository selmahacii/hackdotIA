#include "gps.h"
#include "device_config.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"

static const char *TAG = "GPS";
#define UART_BUF_SIZE 512

static SemaphoreHandle_t s_gps_mutex = NULL;
static gps_data_t s_current_gps = {
    .gps_fix_valid = false,
    .has_coordinates = false,
    .latitude = 0.0f,
    .longitude = 0.0f
};

esp_err_t gps_init(void)
{
    if (!s_gps_mutex) {
        s_gps_mutex = xSemaphoreCreateMutex();
    }

    uart_config_t uart_config = {
        .baud_rate = GPS_BAUD_RATE,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    ESP_ERROR_CHECK(uart_param_config(GPS_UART_PORT, &uart_config));
    ESP_ERROR_CHECK(uart_set_pin(GPS_UART_PORT, PIN_GPS_TX, PIN_GPS_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(GPS_UART_PORT, UART_BUF_SIZE * 2, 0, 0, NULL, 0));

    ESP_LOGI(TAG, "GPS UART2 initialized on TX=%d, RX=%d at %d baud", PIN_GPS_TX, PIN_GPS_RX, GPS_BAUD_RATE);
    return ESP_OK;
}

static bool verify_nmea_checksum(const char *sentence)
{
    if (!sentence || sentence[0] != '$') {
        return false;
    }

    const char *asterisk = strchr(sentence, '*');
    if (!asterisk) {
        return false;
    }

    uint8_t calculated_crc = 0;
    for (const char *p = sentence + 1; p < asterisk; p++) {
        calculated_crc ^= (uint8_t)(*p);
    }

    unsigned int expected_crc = 0;
    if (sscanf(asterisk + 1, "%2x", &expected_crc) != 1) {
        return false;
    }

    return (calculated_crc == (uint8_t)expected_crc);
}

bool gps_parse_rmc(const char *sentence, gps_data_t *out_data)
{
    if (!sentence || !out_data) {
        return false;
    }

    /* Check prefix: must be $GPRMC or $GNRMC */
    if (strncmp(sentence, "$GPRMC", 6) != 0 && strncmp(sentence, "$GNRMC", 6) != 0) {
        return false;
    }

    if (!verify_nmea_checksum(sentence)) {
        ESP_LOGD(TAG, "NMEA Checksum failed: %s", sentence);
        return false;
    }

    /* Duplicate sentence for token parsing */
    char buffer[128];
    strncpy(buffer, sentence, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    char *saveptr;
    char *token = strtok_r(buffer, ",", &saveptr);
    int field_idx = 0;

    char status = 'V';
    char lat_str[16] = {0};
    char ns = 'N';
    char lon_str[16] = {0};
    char ew = 'E';

    while (token != NULL) {
        switch (field_idx) {
            case 2: status = token[0]; break;
            case 3: strncpy(lat_str, token, sizeof(lat_str) - 1); break;
            case 4: ns = token[0]; break;
            case 5: strncpy(lon_str, token, sizeof(lon_str) - 1); break;
            case 6: ew = token[0]; break;
            default: break;
        }
        token = strtok_r(NULL, ",", &saveptr);
        field_idx++;
    }

    /*
     * CRITICAL CONTRACT ENFORCEMENT:
     * When status != 'A' (fix not active), coordinates MUST be invalidated.
     * gps_fix_valid = false, has_coordinates = false.
     * Never transmit 0.0 or stale coordinates!
     */
    if (status != 'A' || strlen(lat_str) < 4 || strlen(lon_str) < 5) {
        out_data->gps_fix_valid = false;
        out_data->has_coordinates = false;
        out_data->latitude = 0.0f;
        out_data->longitude = 0.0f;
        return true;
    }

    /* Parse Latitude: ddmm.mmmm -> decimal degrees */
    float raw_lat = strtof(lat_str, NULL);
    int deg_lat = (int)(raw_lat / 100.0f);
    float min_lat = raw_lat - (deg_lat * 100.0f);
    float dec_lat = (float)deg_lat + (min_lat / 60.0f);
    if (ns == 'S' || ns == 's') dec_lat = -dec_lat;

    /* Parse Longitude: dddmm.mmmm -> decimal degrees */
    float raw_lon = strtof(lon_str, NULL);
    int deg_lon = (int)(raw_lon / 100.0f);
    float min_lon = raw_lon - (deg_lon * 100.0f);
    float dec_lon = (float)deg_lon + (min_lon / 60.0f);
    if (ew == 'W' || ew == 'w') dec_lon = -dec_lon;

    /* Range bounds validation */
    if (dec_lat < -90.0f || dec_lat > 90.0f || dec_lon < -180.0f || dec_lon > 180.0f) {
        out_data->gps_fix_valid = false;
        out_data->has_coordinates = false;
        return true;
    }

    out_data->gps_fix_valid = true;
    out_data->has_coordinates = true;
    out_data->latitude = dec_lat;
    out_data->longitude = dec_lon;

    return true;
}

void gps_get_latest_data(gps_data_t *out_data)
{
    if (!out_data || !s_gps_mutex) {
        return;
    }
    if (xSemaphoreTake(s_gps_mutex, pdMS_TO_TICKS(50)) == pdTRUE) {
        *out_data = s_current_gps;
        xSemaphoreGive(s_gps_mutex);
    }
}

void gps_task(void *pvParameters)
{
    uint8_t line_buffer[128];
    int line_pos = 0;

    ESP_LOGI(TAG, "GPS Background processing task started");

    while (1) {
        uint8_t ch = 0;
        int len = uart_read_bytes(GPS_UART_PORT, &ch, 1, pdMS_TO_TICKS(100));
        if (len > 0) {
            if (ch == '\n' || ch == '\r') {
                if (line_pos > 0) {
                    line_buffer[line_pos] = '\0';
                    gps_data_t parsed;
                    if (gps_parse_rmc((char *)line_buffer, &parsed)) {
                        if (xSemaphoreTake(s_gps_mutex, pdMS_TO_TICKS(50)) == pdTRUE) {
                            s_current_gps = parsed;
                            xSemaphoreGive(s_gps_mutex);
                        }
                    }
                    line_pos = 0;
                }
            } else if (line_pos < sizeof(line_buffer) - 1) {
                line_buffer[line_pos++] = ch;
            } else {
                /* Buffer overflow protection */
                line_pos = 0;
            }
        }
    }
}
