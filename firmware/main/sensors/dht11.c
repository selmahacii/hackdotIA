#include "dht11.h"
#include "device_config.h"

#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "rom/ets_sys.h"

static const char *TAG = "DHT11";
static int64_t s_last_read_time_us = 0;
static dht11_data_t s_cached_data = {
    .temperature_c = 22.0f,
    .humidity_percent = 45.0f,
    .is_valid = false
};

esp_err_t dht11_init(void)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << PIN_DHT11),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t ret = gpio_config(&io_conf);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "DHT11 initialized on GPIO %d", PIN_DHT11);
    }
    return ret;
}

static inline int wait_for_level(int level, uint32_t timeout_us)
{
    uint32_t elapsed = 0;
    while (gpio_get_level(PIN_DHT11) != level) {
        if (++elapsed > timeout_us) {
            return -1;
        }
        ets_delay_us(1);
    }
    return elapsed;
}

esp_err_t dht11_read(dht11_data_t *out_data)
{
    if (!out_data) {
        return ESP_ERR_INVALID_ARG;
    }

    int64_t now_us = esp_timer_get_time();
    /* Rate limiting: return cached sample if called more frequently than 2 seconds */
    if (s_last_read_time_us > 0 && (now_us - s_last_read_time_us) < (DHT11_MIN_READ_INTERVAL_MS * 1000LL)) {
        *out_data = s_cached_data;
        return s_cached_data.is_valid ? ESP_OK : ESP_ERR_TIMEOUT;
    }

    uint8_t data[5] = {0};

    /* Send start signal to DHT11 */
    gpio_set_direction(PIN_DHT11, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_DHT11, 0);
    ets_delay_us(20000); /* Low for 20ms */

    gpio_set_level(PIN_DHT11, 1);
    ets_delay_us(30);    /* High for 30us */
    gpio_set_direction(PIN_DHT11, GPIO_MODE_INPUT);

    /* Await DHT11 response: 80us low, then 80us high */
    if (wait_for_level(0, 100) < 0 || wait_for_level(1, 100) < 0 || wait_for_level(0, 100) < 0) {
        out_data->is_valid = false;
        return ESP_ERR_TIMEOUT;
    }

    /* Read 40 bits (5 bytes) */
    for (int i = 0; i < 40; ++i) {
        if (wait_for_level(1, 70) < 0) {
            out_data->is_valid = false;
            return ESP_ERR_TIMEOUT;
        }

        uint32_t high_duration = 0;
        while (gpio_get_level(PIN_DHT11) == 1) {
            if (++high_duration > 100) {
                out_data->is_valid = false;
                return ESP_ERR_TIMEOUT;
            }
            ets_delay_us(1);
        }

        uint8_t byte_idx = i / 8;
        data[byte_idx] <<= 1;
        if (high_duration > 35) { /* High > 35us indicates bit '1' */
            data[byte_idx] |= 1;
        }
    }

    /* Verify Checksum */
    uint8_t checksum = data[0] + data[1] + data[2] + data[3];
    if (checksum != data[4]) {
        ESP_LOGW(TAG, "DHT11 Checksum mismatch: calc=%d, got=%d", checksum, data[4]);
        out_data->is_valid = false;
        return ESP_ERR_INVALID_CRC;
    }

    out_data->humidity_percent = (float)data[0] + (float)data[1] * 0.1f;
    out_data->temperature_c = (float)data[2] + (float)data[3] * 0.1f;
    out_data->is_valid = true;

    s_cached_data = *out_data;
    s_last_read_time_us = now_us;

    return ESP_OK;
}
