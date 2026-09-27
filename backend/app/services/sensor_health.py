import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.config import Settings, settings
from app.models.device import Device
from app.models.enums import SensorHealthStatus
from app.models.measurement import Measurement


@dataclass
class SensorHealthEvaluation:
    max30102_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    dht11_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    mpu6050_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    gps_status: SensorHealthStatus = SensorHealthStatus.UNKNOWN
    details: dict[str, Any] = field(default_factory=dict)


class SensorHealthService:
    """
    Deterministic domain service evaluating hardware and sensor health.
    Evaluates MAX30102, DHT11, MPU6050, GPS, battery level, and device connectivity.
    Does NOT produce medical diagnostics or trigger medical emergency alerts.
    """

    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or settings

    def evaluate(
        self,
        measurement: Measurement,
        history: Sequence[Measurement] = (),
        device: Device | None = None,
        now: datetime | None = None,
    ) -> SensorHealthEvaluation:
        """
        Evaluates the health of all 4 physical sensors based on current measurement
        and chronological history.
        """
        # Ensure history is sorted chronologically (ascending measured_at)
        sorted_history = sorted(
            [
                m
                for m in history
                if m.id != measurement.id and m.measured_at <= measurement.measured_at
            ],
            key=lambda m: m.measured_at,
        )

        reasons: dict[str, str | None] = {}

        # 1. MAX30102 Evaluation
        max30102_status, max30102_reason = self._evaluate_max30102(measurement, sorted_history)
        reasons["max30102"] = max30102_reason

        # 2. DHT11 Evaluation
        dht11_status, dht11_reason = self._evaluate_dht11(measurement, sorted_history)
        reasons["dht11"] = dht11_reason

        # 3. MPU6050 Evaluation
        mpu6050_status, mpu6050_reason = self._evaluate_mpu6050(measurement, sorted_history)
        reasons["mpu6050"] = mpu6050_reason

        # 4. GPS Evaluation
        gps_status, gps_reason = self._evaluate_gps(measurement, sorted_history)
        reasons["gps"] = gps_reason

        # 5. Battery & Device Connectivity Diagnostics
        battery_diag = self._evaluate_battery(measurement)
        device_diag = self._evaluate_device_offline(measurement, device, now)

        details: dict[str, Any] = {
            "reasons": reasons,
            "battery": battery_diag,
            "device": device_diag,
        }

        return SensorHealthEvaluation(
            max30102_status=max30102_status,
            dht11_status=dht11_status,
            mpu6050_status=mpu6050_status,
            gps_status=gps_status,
            details=details,
        )

    def _evaluate_max30102(
        self,
        m: Measurement,
        history: list[Measurement],
    ) -> tuple[SensorHealthStatus, str | None]:
        # Rule 1 — No contact
        if not m.finger_detected:
            return SensorHealthStatus.NO_CONTACT, "finger_not_detected"

        # Finger is detected
        has_valid_bpm = m.bpm is not None and m.bpm > 0
        has_valid_spo2 = m.spo2 is not None and m.spo2 > 0

        if has_valid_bpm and has_valid_spo2:
            return SensorHealthStatus.HEALTHY, None

        # BPM is absent (None or 0) while finger is detected
        # Check motion
        movement_now = self._is_movement_detected(m)
        recent_movement = movement_now or any(self._is_movement_detected(h) for h in history[-5:])

        # Calculate duration of BPM absence with finger detected
        absence_duration_s = self._calculate_consecutive_duration(
            current=m,
            history=history,
            predicate=lambda item: item.finger_detected and (item.bpm is None or item.bpm == 0),
        )

        if absence_duration_s >= self.config.SENSOR_MAX30102_ABSENCE_THRESHOLD_S:
            if recent_movement:
                # Rule 2 — BPM absent with movement >= threshold
                return SensorHealthStatus.SUSPECT, "bpm_absent_with_movement"
            else:
                # Rule 3 — BPM absent without movement >= threshold
                return SensorHealthStatus.UNKNOWN, "bpm_absent_no_movement"

        # Under threshold: transient contact acquisition or searching
        if recent_movement:
            return SensorHealthStatus.UNKNOWN, "bpm_absent_with_movement"
        return SensorHealthStatus.UNKNOWN, "bpm_absent_no_movement"

    def _evaluate_dht11(
        self,
        m: Measurement,
        history: list[Measurement],
    ) -> tuple[SensorHealthStatus, str | None]:
        if m.temperature_c is None and m.humidity_percent is None:
            return SensorHealthStatus.UNKNOWN, None

        # Rule 1 — Sampling too fast
        if history:
            prev_dht = next(
                (
                    h
                    for h in reversed(history)
                    if h.temperature_c is not None or h.humidity_percent is not None
                ),
                None,
            )
            if prev_dht:
                delta_s = (m.measured_at - prev_dht.measured_at).total_seconds()
                if 0 <= delta_s < self.config.SENSOR_DHT11_MIN_INTERVAL_S:
                    return SensorHealthStatus.SUSPECT, "dht11_sampling_too_fast"

        # Rule 2 — Frozen humidity
        if m.humidity_percent is not None:
            consecutive_same_humidity: list[Measurement] = [m]
            for h in reversed(history):
                if (
                    h.humidity_percent is not None
                    and abs(h.humidity_percent - m.humidity_percent) < 1e-4
                ):
                    consecutive_same_humidity.append(h)
                else:
                    break

            if len(consecutive_same_humidity) >= 3:
                earliest_time = consecutive_same_humidity[-1].measured_at
                frozen_duration_s = (m.measured_at - earliest_time).total_seconds()
                if frozen_duration_s >= self.config.SENSOR_DHT11_FROZEN_DURATION_S:
                    return SensorHealthStatus.SUSPECT, "humidity_frozen"

        return SensorHealthStatus.HEALTHY, None

    def _evaluate_mpu6050(
        self,
        m: Measurement,
        history: list[Measurement],
    ) -> tuple[SensorHealthStatus, str | None]:
        if m.accel_x_g is None or m.accel_y_g is None or m.accel_z_g is None:
            return SensorHealthStatus.UNKNOWN, None

        # Rule — Flatline (accel_x == 0, accel_y == 0, accel_z == 0)
        is_current_zero = (
            abs(m.accel_x_g) < 1e-4 and abs(m.accel_y_g) < 1e-4 and abs(m.accel_z_g) < 1e-4
        )
        if is_current_zero:
            consecutive_zero_count = 1
            for h in reversed(history):
                if (
                    h.accel_x_g is not None
                    and h.accel_y_g is not None
                    and h.accel_z_g is not None
                    and abs(h.accel_x_g) < 1e-4
                    and abs(h.accel_y_g) < 1e-4
                    and abs(h.accel_z_g) < 1e-4
                ):
                    consecutive_zero_count += 1
                else:
                    break

            if consecutive_zero_count >= self.config.SENSOR_MPU6050_FLATLINE_SAMPLES:
                return SensorHealthStatus.SUSPECT, "imu_flatline"

        return SensorHealthStatus.HEALTHY, None

    def _evaluate_gps(
        self,
        m: Measurement,
        history: list[Measurement],
    ) -> tuple[SensorHealthStatus, str | None]:
        # Rule — GPS fix valid
        if m.gps_fix_valid:
            return SensorHealthStatus.HEALTHY, None

        # GPS fix invalid: check duration
        no_fix_duration_s = self._calculate_consecutive_duration(
            current=m,
            history=history,
            predicate=lambda item: not item.gps_fix_valid,
        )

        if no_fix_duration_s > self.config.SENSOR_GPS_NO_FIX_DURATION_S:
            return SensorHealthStatus.UNAVAILABLE, "gps_no_fix"

        return SensorHealthStatus.NO_CONTACT, "gps_searching_fix"

    def _evaluate_battery(self, m: Measurement) -> dict[str, Any]:
        if m.battery_level is None:
            return {"level": None, "status": "UNKNOWN"}

        if m.battery_level < self.config.BATTERY_CRITICAL_THRESHOLD:
            status = "CRITICAL"
        elif m.battery_level < self.config.BATTERY_WARNING_THRESHOLD:
            status = "WARNING"
        else:
            status = "NORMAL"

        return {"level": m.battery_level, "status": status}

    def _evaluate_device_offline(
        self,
        m: Measurement,
        device: Device | None,
        now: datetime | None,
    ) -> dict[str, Any]:
        curr_time = now or datetime.now(UTC)
        ref_time = device.last_seen_at if (device and device.last_seen_at) else m.measured_at

        delta_s = (curr_time - ref_time).total_seconds()
        if delta_s > self.config.DEVICE_OFFLINE_THRESHOLD_S:
            return {
                "status": "UNAVAILABLE",
                "reason": "device_offline",
                "elapsed_s": round(delta_s, 1),
            }

        return {"status": "ONLINE", "reason": None, "elapsed_s": round(delta_s, 1)}

    @staticmethod
    def _is_movement_detected(m: Measurement) -> bool:
        if m.accel_magnitude_g is not None:
            return abs(m.accel_magnitude_g - 1.0) >= 0.08
        if m.accel_x_g is not None and m.accel_y_g is not None and m.accel_z_g is not None:
            mag = math.sqrt(m.accel_x_g**2 + m.accel_y_g**2 + m.accel_z_g**2)
            return abs(mag - 1.0) >= 0.08
        return False

    @staticmethod
    def _calculate_consecutive_duration(
        current: Measurement,
        history: list[Measurement],
        predicate: Any,
    ) -> float:
        if not predicate(current):
            return 0.0

        earliest_time = current.measured_at
        for h in reversed(history):
            if predicate(h):
                earliest_time = h.measured_at
            else:
                break

        return max(0.0, (current.measured_at - earliest_time).total_seconds())
