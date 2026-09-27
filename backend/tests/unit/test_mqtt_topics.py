from app.mqtt.topics import build_topic, get_topic_filter, parse_topic


def test_parse_valid_topics() -> None:
    assert parse_topic("elderly/ESP32-ELDERLY-001/telemetry") == ("ESP32-ELDERLY-001", "telemetry")
    assert parse_topic("elderly/ESP32-ELDERLY-001/status") == ("ESP32-ELDERLY-001", "status")
    assert parse_topic("elderly/ESP32-ELDERLY-001/health") == ("ESP32-ELDERLY-001", "health")


def test_parse_custom_prefix() -> None:
    assert parse_topic("custom/ESP32-01/telemetry", prefix="custom") == ("ESP32-01", "telemetry")
    assert parse_topic("elderly/ESP32-01/telemetry", prefix="custom") is None


def test_parse_invalid_topics() -> None:
    assert parse_topic("elderly/ESP32-01") is None
    assert parse_topic("elderly/ESP32-01/invalid_type") is None
    assert parse_topic("elderly/ESP32-01/telemetry/extra") is None
    assert parse_topic("wrong_prefix/ESP32-01/telemetry") is None
    assert parse_topic("") is None


def test_build_topic() -> None:
    assert build_topic("ESP32-001", "telemetry") == "elderly/ESP32-001/telemetry"
    assert build_topic("ESP32-001", "status") == "elderly/ESP32-001/status"
    assert build_topic("ESP32-001", "health", prefix="dept") == "dept/ESP32-001/health"


def test_get_topic_filter() -> None:
    filters = get_topic_filter()
    assert "elderly/+/telemetry" in filters
    assert "elderly/+/status" in filters
    assert "elderly/+/health" in filters
