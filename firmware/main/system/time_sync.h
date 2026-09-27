#ifndef TIME_SYNC_H
#define TIME_SYNC_H

#include <stdbool.h>
#include <stddef.h>
#include <time.h>

typedef enum {
    TIME_STATE_NOT_SYNCED = 0,
    TIME_STATE_SYNCING,
    TIME_STATE_SYNCED
} time_sync_state_t;

/**
 * Initializes the SNTP client to synchronize UTC clock via pool.ntp.org.
 */
void time_sync_init(void);

/**
 * Checks whether the system RTC clock has been synchronized with NTP.
 * Returns true only if UTC time is valid (epoch > 1700000000).
 */
bool time_sync_is_synced(void);

/**
 * Returns current internal synchronization state.
 */
time_sync_state_t time_sync_get_state(void);

/**
 * Fills buffer with ISO-8601 UTC timestamp format: YYYY-MM-DDTHH:MM:SSZ
 * Returns true on success, false if time is not synced.
 */
bool time_sync_get_iso8601(char *buffer, size_t max_len);

/**
 * Generates an RFC 4122 compliant UUID v4 string (e.g. 550e8400-e29b-41d4-a716-446655440000).
 * Uses ESP32 True Random Number Generator (TRNG).
 */
void time_sync_generate_uuid_v4(char *buffer, size_t max_len);

#endif /* TIME_SYNC_H */
