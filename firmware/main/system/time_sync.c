#include "time_sync.h"
#include "device_config.h"

#include <stdio.h>
#include <string.h>
#include "esp_sntp.h"
#include "esp_log.h"
#include "esp_random.h"

static const char *TAG = "TIME_SYNC";
static time_sync_state_t s_sync_state = TIME_STATE_NOT_SYNCED;

void time_sync_init(void)
{
    ESP_LOGI(TAG, "Initializing SNTP client with server: %s", NTP_SERVER_NAME);
    s_sync_state = TIME_STATE_SYNCING;

    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, NTP_SERVER_NAME);
    esp_sntp_init();
}

bool time_sync_is_synced(void)
{
    time_t now = 0;
    time(&now);
    /* Epoch threshold 1700000000 corresponds to mid-November 2023 */
    if (now > 1700000000) {
        s_sync_state = TIME_STATE_SYNCED;
        return true;
    }
    return false;
}

time_sync_state_t time_sync_get_state(void)
{
    time_sync_is_synced();
    return s_sync_state;
}

bool time_sync_get_iso8601(char *buffer, size_t max_len)
{
    if (!buffer || max_len < 21) {
        return false;
    }

    if (!time_sync_is_synced()) {
        buffer[0] = '\0';
        return false;
    }

    time_t now = 0;
    time(&now);
    struct tm timeinfo;
    gmtime_r(&now, &timeinfo);

    /* Produce ISO-8601 UTC timestamp: YYYY-MM-DDTHH:MM:SSZ */
    strftime(buffer, max_len, "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return true;
}

void time_sync_generate_uuid_v4(char *buffer, size_t max_len)
{
    if (!buffer || max_len < 37) {
        return;
    }

    uint8_t bytes[16];
    for (int i = 0; i < 16; i += 4) {
        uint32_t r = esp_random();
        bytes[i]     = (uint8_t)(r & 0xFF);
        bytes[i + 1] = (uint8_t)((r >> 8) & 0xFF);
        bytes[i + 2] = (uint8_t)((r >> 16) & 0xFF);
        bytes[i + 3] = (uint8_t)((r >> 24) & 0xFF);
    }

    /* RFC 4122 compliance */
    bytes[6] = (bytes[6] & 0x0F) | 0x40; /* Version 4 */
    bytes[8] = (bytes[8] & 0x3F) | 0x80; /* Variant 1 */

    snprintf(buffer, max_len,
             "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
             bytes[0], bytes[1], bytes[2], bytes[3],
             bytes[4], bytes[5],
             bytes[6], bytes[7],
             bytes[8], bytes[9],
             bytes[10], bytes[11], bytes[12], bytes[13], bytes[14], bytes[15]);
}
