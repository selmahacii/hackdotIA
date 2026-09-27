#include "app_mqtt.h"
#include "device_config.h"

#include <stdio.h>
#include <string.h>
#include "esp_event.h"
#include "esp_log.h"
#include "mqtt_client.h"

static const char *TAG = "MQTT_APP";
static esp_mqtt_client_handle_t s_mqtt_client = NULL;
static bool s_is_connected = false;

static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data)
{
    (void)handler_args;
    (void)base;
    esp_mqtt_event_handle_t event = (esp_mqtt_event_handle_t)event_data;

    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED:
        s_is_connected = true;
        ESP_LOGI(TAG, "Connected to MQTT broker: %s", CONFIG_MQTT_BROKER_URI);
        break;

    case MQTT_EVENT_DISCONNECTED:
        s_is_connected = false;
        ESP_LOGW(TAG, "Disconnected from MQTT broker");
        break;

    case MQTT_EVENT_PUBLISHED:
        ESP_LOGD(TAG, "MQTT message delivered (msg_id=%d, QoS 1 ACK received)", event->msg_id);
        break;

    case MQTT_EVENT_ERROR:
        ESP_LOGE(TAG, "MQTT Error encountered");
        break;

    default:
        break;
    }
}

esp_err_t mqtt_app_start(void)
{
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = CONFIG_MQTT_BROKER_URI,
    };

    s_mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    if (!s_mqtt_client) {
        ESP_LOGE(TAG, "Failed to initialize MQTT client");
        return ESP_FAIL;
    }

    ESP_ERROR_CHECK(esp_mqtt_client_register_event(s_mqtt_client,
                                                   ESP_EVENT_ANY_ID,
                                                   mqtt_event_handler,
                                                   NULL));
    ESP_ERROR_CHECK(esp_mqtt_client_start(s_mqtt_client));

    ESP_LOGI(TAG, "MQTT client started");
    return ESP_OK;
}

bool mqtt_app_is_connected(void)
{
    return s_is_connected;
}

bool mqtt_app_publish_telemetry(const char *json_payload)
{
    if (!s_mqtt_client || !s_is_connected || !json_payload) {
        return false;
    }

    char topic[96];
    snprintf(topic, sizeof(topic), "%s%s%s",
             MQTT_TOPIC_PREFIX, CONFIG_DEVICE_UID, MQTT_TELEMETRY_SUFFIX);

    int msg_id = esp_mqtt_client_publish(s_mqtt_client,
                                         topic,
                                         json_payload,
                                         0,
                                         MQTT_QOS_LEVEL,
                                         0);

    if (msg_id == -1) {
        ESP_LOGW(TAG, "Failed to enqueue MQTT message on topic '%s'", topic);
        return false;
    }

    ESP_LOGI(TAG, "Published telemetry (msg_id=%d, topic='%s', bytes=%u)",
             msg_id, topic, (unsigned int)strlen(json_payload));
    return true;
}
