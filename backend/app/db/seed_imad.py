"""Seed realistic production telemetry, user account, alerts and resident profile for Imad Ghobrini on 27-09-2026."""

import asyncio
import os
import sys
import uuid
from datetime import UTC, date, datetime, timedelta

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import delete, select
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.device import Device
from app.models.elderly import ElderlyPerson
from app.models.enums import (
    AIAnalysisStatus,
    AIProvider,
    AlertSeverity,
    AlertSource,
    AlertStatus,
    AlertType,
    DeviceStatus,
    SensorHealthStatus,
    UserRole,
)
from app.models.measurement import Measurement
from app.models.sensor_health import SensorHealth
from app.models.user import User


async def seed_imad_data() -> None:
    print("🚀 Seeding realistic production data for Imad Ghobrini on 27-09-2026...")

    async with AsyncSessionLocal() as session:
        # 1. Create or update User Account
        user_query = select(User).where(User.username == "imad.ghobrini")
        user_res = await session.execute(user_query)
        imad_user = user_res.scalars().first()

        if not imad_user:
            imad_user = User(
                id=uuid.uuid4(),
                username="imad.ghobrini",
                email="imad.ghobrini@smarteldery.health",
                hashed_password=hash_password("Imad2026!Pass"),
                full_name="Imad Ghobrini",
                role=UserRole.SUPERADMIN,
                is_active=True,
                assigned_elderly_ids=[],
                last_login_at=datetime(2026, 9, 27, 16, 45, 0, tzinfo=UTC),
                created_at=datetime(2026, 9, 27, 8, 0, 0, tzinfo=UTC),
                updated_at=datetime(2026, 9, 27, 16, 45, 0, tzinfo=UTC),
            )
            session.add(imad_user)
            print("  ✅ Created user 'imad.ghobrini' with role SUPERADMIN (Password: Imad2026!Pass)")
        else:
            imad_user.role = UserRole.SUPERADMIN
            imad_user.hashed_password = hash_password("Imad2026!Pass")
            imad_user.is_active = True
            imad_user.last_login_at = datetime(2026, 9, 27, 16, 45, 0, tzinfo=UTC)
            print("  ✅ Updated user 'imad.ghobrini' to SUPERADMIN")

        await session.commit()

        # 2. Create or find Elderly Resident Profile for Imad Ghobrini
        elderly_query = select(ElderlyPerson).where(
            ElderlyPerson.first_name == "Imad",
            ElderlyPerson.last_name == "Ghobrini",
        )
        elderly_res = await session.execute(elderly_query)
        imad_elderly = elderly_res.scalars().first()

        if not imad_elderly:
            imad_elderly = ElderlyPerson(
                id=uuid.uuid4(),
                first_name="Imad",
                last_name="Ghobrini",
                date_of_birth=date(1952, 4, 18),
                phone="+33 6 12 34 56 78",
                emergency_contact_name="Sarah Ghobrini (Fille)",
                emergency_contact_phone="+33 6 98 76 54 32",
                is_active=True,
                created_at=datetime(2026, 9, 27, 7, 30, 0, tzinfo=UTC),
                updated_at=datetime(2026, 9, 27, 16, 45, 0, tzinfo=UTC),
            )
            session.add(imad_elderly)
            await session.commit()
            await session.refresh(imad_elderly)
            print(f"  ✅ Created resident 'Imad Ghobrini' with ID {imad_elderly.id}")
        else:
            print(f"  ℹ️ Found existing resident 'Imad Ghobrini' with ID {imad_elderly.id}")

        # 3. Create or find Device for Imad Ghobrini
        dev_query = select(Device).where(Device.device_uid == "ESP32-IMAD-GHOBRINI-01")
        dev_res = await session.execute(dev_query)
        imad_device = dev_res.scalars().first()

        if not imad_device:
            imad_device = Device(
                id=uuid.uuid4(),
                device_uid="ESP32-IMAD-GHOBRINI-01",
                elderly_id=imad_elderly.id,
                name="Bracelet Médical ESP32 - Imad Ghobrini",
                status=DeviceStatus.ONLINE,
                battery_level=88.5,
                wifi_rssi=-51,
                firmware_version="v2.4.1-clinical",
                capabilities={
                    "type": "WRISTBAND",
                    "hardware": "ESP32-WROOM-32D v1.2",
                    "sensors": ["MAX30102", "MPU6050", "DHT11", "NEO6M_GPS"],
                },
                last_seen_at=datetime(2026, 9, 27, 17, 0, 0, tzinfo=UTC),
                created_at=datetime(2026, 9, 27, 7, 45, 0, tzinfo=UTC),
                updated_at=datetime(2026, 9, 27, 17, 0, 0, tzinfo=UTC),
            )
            session.add(imad_device)
            await session.commit()
            await session.refresh(imad_device)
            print(f"  ✅ Created device 'ESP32-IMAD-GHOBRINI-01' with ID {imad_device.id}")
        else:
            imad_device.elderly_id = imad_elderly.id
            imad_device.status = DeviceStatus.ONLINE
            imad_device.battery_level = 88.5
            imad_device.wifi_rssi = -51
            imad_device.last_seen_at = datetime(2026, 9, 27, 17, 0, 0, tzinfo=UTC)
            await session.commit()
            print(f"  ℹ️ Updated device 'ESP32-IMAD-GHOBRINI-01' with ID {imad_device.id}")

        # 4. Clean old records for this resident to ensure clean, consistent data
        # Delete existing alerts (and cascade AI analyses)
        existing_alerts = await session.execute(
            select(Alert).where(Alert.elderly_id == imad_elderly.id)
        )
        for a in existing_alerts.scalars().all():
            await session.execute(delete(AIAnalysis).where(AIAnalysis.alert_id == a.id))
            await session.delete(a)

        # Delete existing sensor health
        await session.execute(
            delete(SensorHealth).where(SensorHealth.device_id == imad_device.id)
        )
        # Delete existing measurements
        await session.execute(
            delete(Measurement).where(Measurement.elderly_id == imad_elderly.id)
        )
        await session.commit()

        # 5. Insert diverse chronological measurements throughout 27-09-2026
        telemetry_schedule = [
            # Morning rest (08:00)
            {
                "time": datetime(2026, 9, 27, 8, 0, 0, tzinfo=UTC),
                "bpm": 66.0,
                "spo2": 98.5,
                "finger": True,
                "temp": 36.5,
                "humidity": 48.0,
                "ax": 0.05, "ay": 0.12, "az": 0.98, "amag": 0.99,
                "lat": 48.8566, "lon": 2.3522, "gps_valid": True,
                "battery": 98.0, "rssi": -52,
            },
            # Morning awakening & light walk (09:15)
            {
                "time": datetime(2026, 9, 27, 9, 15, 0, tzinfo=UTC),
                "bpm": 74.0,
                "spo2": 98.0,
                "finger": True,
                "temp": 36.6,
                "humidity": 47.5,
                "ax": 0.14, "ay": 0.22, "az": 1.05, "amag": 1.08,
                "lat": 48.8568, "lon": 2.3524, "gps_valid": True,
                "battery": 96.0, "rssi": -54,
            },
            # Garden stroll (10:45)
            {
                "time": datetime(2026, 9, 27, 10, 45, 0, tzinfo=UTC),
                "bpm": 86.0,
                "spo2": 97.5,
                "finger": True,
                "temp": 36.8,
                "humidity": 45.0,
                "ax": 0.25, "ay": 0.38, "az": 1.15, "amag": 1.23,
                "lat": 48.8572, "lon": 2.3530, "gps_valid": True,
                "battery": 93.0, "rssi": -58,
            },
            # Lunch resting (12:30)
            {
                "time": datetime(2026, 9, 27, 12, 30, 0, tzinfo=UTC),
                "bpm": 72.0,
                "spo2": 98.0,
                "finger": True,
                "temp": 36.9,
                "humidity": 46.0,
                "ax": 0.02, "ay": 0.08, "az": 0.99, "amag": 1.00,
                "lat": 48.8566, "lon": 2.3522, "gps_valid": True,
                "battery": 91.0, "rssi": -53,
            },
            # Sudden slip and impact event (14:32:00)
            {
                "time": datetime(2026, 9, 27, 14, 32, 0, tzinfo=UTC),
                "bpm": 114.0,
                "spo2": 95.5,
                "finger": True,
                "temp": 36.8,
                "humidity": 46.5,
                "ax": 2.25, "ay": -1.85, "az": 2.30, "amag": 3.65,
                "lat": 48.8566, "lon": 2.3522, "gps_valid": True,
                "battery": 89.5, "rssi": -55,
            },
            # Post-fall immobility on floor (14:32:30)
            {
                "time": datetime(2026, 9, 27, 14, 32, 30, tzinfo=UTC),
                "bpm": 118.0,
                "spo2": 95.0,
                "finger": True,
                "temp": 36.8,
                "humidity": 46.5,
                "ax": 0.01, "ay": 0.02, "az": 0.99, "amag": 1.00,
                "lat": 48.8566, "lon": 2.3522, "gps_valid": True,
                "battery": 89.4, "rssi": -55,
            },
            # Caregiver assistance arrival (14:36:00)
            {
                "time": datetime(2026, 9, 27, 14, 36, 0, tzinfo=UTC),
                "bpm": 102.0,
                "spo2": 96.5,
                "finger": True,
                "temp": 36.7,
                "humidity": 47.0,
                "ax": 0.12, "ay": 0.18, "az": 1.02, "amag": 1.05,
                "lat": 48.8566, "lon": 2.3522, "gps_valid": True,
                "battery": 89.2, "rssi": -54,
            },
            # Resting in recovery armchair (15:50)
            {
                "time": datetime(2026, 9, 27, 15, 50, 0, tzinfo=UTC),
                "bpm": 76.0,
                "spo2": 98.2,
                "finger": True,
                "temp": 36.7,
                "humidity": 48.0,
                "ax": 0.04, "ay": 0.09, "az": 0.98, "amag": 0.99,
                "lat": 48.8566, "lon": 2.3522, "gps_valid": True,
                "battery": 88.8, "rssi": -52,
            },
            # Real-time state (17:00:00)
            {
                "time": datetime(2026, 9, 27, 17, 0, 0, tzinfo=UTC),
                "bpm": 71.0,
                "spo2": 98.8,
                "finger": True,
                "temp": 36.7,
                "humidity": 47.8,
                "ax": 0.06, "ay": 0.10, "az": 1.01, "amag": 1.02,
                "lat": 48.8566, "lon": 2.3522, "gps_valid": True,
                "battery": 88.5, "rssi": -51,
            },
        ]

        saved_measurements = []
        fall_measurement = None

        for item in telemetry_schedule:
            meas = Measurement(
                id=uuid.uuid4(),
                event_id=uuid.uuid4(),
                device_id=imad_device.id,
                elderly_id=imad_elderly.id,
                measured_at=item["time"],
                received_at=item["time"] + timedelta(milliseconds=250),
                bpm=item["bpm"],
                spo2=item["spo2"],
                finger_detected=item["finger"],
                temperature_c=item["temp"],
                humidity_percent=item["humidity"],
                accel_x_g=item["ax"],
                accel_y_g=item["ay"],
                accel_z_g=item["az"],
                accel_magnitude_g=item["amag"],
                gps_latitude=item["lat"],
                gps_longitude=item["lon"],
                gps_fix_valid=item["gps_valid"],
                battery_level=item["battery"],
                wifi_rssi=item["rssi"],
            )
            session.add(meas)
            saved_measurements.append(meas)
            if item["amag"] > 3.0:
                fall_measurement = meas

        await session.commit()
        print(f"  ✅ Inserted {len(saved_measurements)} realistic telemetry points for 27-09-2026")

        # 6. Insert Hardware Sensor Health record for device
        sh = SensorHealth(
            id=uuid.uuid4(),
            device_id=imad_device.id,
            measurement_id=saved_measurements[-1].id,
            max30102_status=SensorHealthStatus.HEALTHY,
            mpu6050_status=SensorHealthStatus.HEALTHY,
            dht11_status=SensorHealthStatus.HEALTHY,
            gps_status=SensorHealthStatus.HEALTHY,
            details={
                "i2c_bus": "active_400khz",
                "sda_pin": 21,
                "scl_pin": 22,
                "mpu6050_whoami": "0x68_ok",
                "max30102_part_id": "0x15_ok",
                "battery_voltage_v": 3.92,
                "wifi_rssi_dbm": -51,
            },
            checked_at=datetime(2026, 9, 27, 17, 0, 0, tzinfo=UTC),
        )
        session.add(sh)
        await session.commit()
        print("  ✅ Inserted Sensor Health diagnostics for ESP32-IMAD-GHOBRINI-01")

        # 7. Insert Diverse Alerts on 27-09-2026
        # Alert A: Critical Fall Suspected
        fall_alert = Alert(
            id=uuid.uuid4(),
            elderly_id=imad_elderly.id,
            device_id=imad_device.id,
            alert_type=AlertType.FALL_SUSPECTED,
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            title="Suspicion de chute violente détectée (3.65g)",
            description="Pic d'accélération à 3.65g enregistré sur le poignet suivi d'une phase d'immobilité prolongée de 30 secondes au sol.",
            source=AlertSource.RULE_ENGINE,
            occurred_at=datetime(2026, 9, 27, 14, 32, 15, tzinfo=UTC),
            created_at=datetime(2026, 9, 27, 14, 32, 16, tzinfo=UTC),
            occurrence_count=1,
            dedup_key=f"fall_imad_{uuid.uuid4().hex[:8]}",
            context={
                "measurement_id": str(fall_measurement.id) if fall_measurement else None,
                "accel_magnitude_g": 3.65,
                "impact_axes": {"x": 2.25, "y": -1.85, "z": 2.30},
                "post_impact_immobility_seconds": 30,
                "location": "Chambre Principale 104",
                "resident_name": "Imad Ghobrini",
            },
        )
        session.add(fall_alert)
        await session.commit()
        await session.refresh(fall_alert)

        # AI Enrichment for Fall Alert
        ai_fall = AIAnalysis(
            id=uuid.uuid4(),
            alert_id=fall_alert.id,
            provider=AIProvider.GROQ,
            status=AIAnalysisStatus.COMPLETED,
            risk_level="CRITICAL",
            anomaly_detected=True,
            possible_event="Chute physique brutale avec impact au sol et immobilité immédiate",
            explanation=(
                "Cinématique hautement concordante avec un déséquilibre soudain : le capteur MPU6050 a mesuré un pic transitoire "
                "de 3.65g (seuil critique > 2.8g), immédiatement corrélé à une phase de repos inertiel de 30 secondes et une élévation "
                "de la fréquence cardiaque de 72 à 114 BPM. Données brutes fiables (aucun contact perdu sur MAX30102)."
            ),
            recommended_action=(
                "1. Intervention physique immédiate dans la chambre 104 pour évaluer la conscience et la mobilité. "
                "2. Vérifier les points de contact anatomiques et l'absence de traumatisme. "
                "3. Contrôler les constantes vitales en direct sur la console et acquitter après prise en charge."
            ),
            confidence=0.94,
            model_name="openai/gpt-oss-20b",
            latency_ms=312,
            completed_at=datetime(2026, 9, 27, 14, 32, 18, tzinfo=UTC),
            raw_response={
                "summary": "Impact cinématique à 3.65g suivi d'immobilité",
                "observations": ["Pic 3.65g sur MPU6050", "Immobilité 30s", "Tachycardie réactionnelle 114 BPM"],
                "data_quality": "OPTIMAL",
                "confidence": 0.94,
            },
        )
        session.add(ai_fall)

        # Alert B: High Tachycardia Reaction (Acknowledged)
        tachy_alert = Alert(
            id=uuid.uuid4(),
            elderly_id=imad_elderly.id,
            device_id=imad_device.id,
            alert_type=AlertType.HEART_RATE_ANOMALY,
            severity=AlertSeverity.HIGH,
            status=AlertStatus.ACKNOWLEDGED,
            title="Tachycardie réactionnelle post-événement (118 BPM)",
            description="Fréquence cardiaque mesurée à 118 BPM supérieure au seuil d'alerte haute (100 BPM).",
            source=AlertSource.RULE_ENGINE,
            occurred_at=datetime(2026, 9, 27, 14, 33, 0, tzinfo=UTC),
            created_at=datetime(2026, 9, 27, 14, 33, 2, tzinfo=UTC),
            acknowledged_at=datetime(2026, 9, 27, 14, 36, 10, tzinfo=UTC),
            acknowledged_by="imad.ghobrini",
            occurrence_count=2,
            dedup_key=f"tachy_imad_{uuid.uuid4().hex[:8]}",
            context={
                "bpm": 118.0,
                "baseline_bpm": 66.0,
                "spo2": 95.0,
            },
        )
        session.add(tachy_alert)
        await session.commit()
        await session.refresh(tachy_alert)

        ai_tachy = AIAnalysis(
            id=uuid.uuid4(),
            alert_id=tachy_alert.id,
            provider=AIProvider.GROQ,
            status=AIAnalysisStatus.COMPLETED,
            risk_level="HIGH",
            anomaly_detected=True,
            possible_event="Tachycardie sinusale réactionnelle consécutive au stress de l'impact",
            explanation=(
                "Élévation de la fréquence cardiaque atteignant 118 BPM consécutive à l'incident cinématique précédent. "
                "Le signal PPG MAX30102 présente une onde de pouls bien conformée, excluant un artéfact de mouvement. "
                "SpO2 stable à 95%."
            ),
            recommended_action=(
                "Rassurer le résident, maintenir la position assise de confort et surveiller la régression vers le rythme basal."
            ),
            confidence=0.91,
            model_name="openai/gpt-oss-20b",
            latency_ms=280,
            completed_at=datetime(2026, 9, 27, 14, 33, 5, tzinfo=UTC),
        )
        session.add(ai_tachy)

        # Alert C: Informational Auto-Calibration (Resolved)
        calib_alert = Alert(
            id=uuid.uuid4(),
            elderly_id=imad_elderly.id,
            device_id=imad_device.id,
            alert_type=AlertType.SENSOR_HEALTH,
            severity=AlertSeverity.INFO,
            status=AlertStatus.RESOLVED,
            title="Auto-étalonnage des capteurs I²C effectué avec succès",
            description="Le microcontrôleur ESP32 a recalibré le zéro accélérométrique et vérifié l'intégrité du bus I²C.",
            source=AlertSource.SENSOR_HEALTH,
            occurred_at=datetime(2026, 9, 27, 8, 30, 0, tzinfo=UTC),
            created_at=datetime(2026, 9, 27, 8, 30, 1, tzinfo=UTC),
            resolved_at=datetime(2026, 9, 27, 8, 30, 15, tzinfo=UTC),
            occurrence_count=1,
            dedup_key=f"calib_imad_{uuid.uuid4().hex[:8]}",
            context={"calibration_status": "SUCCESS", "i2c_bus_freq": 400000},
        )
        session.add(calib_alert)
        await session.commit()

        print("  ✅ Inserted 3 diverse alerts (CRITICAL, HIGH, INFO) with Groq AI clinical analyses!")
        print("\n🎉 Seeding complete for Imad Ghobrini on 27-09-2026!")
        print(f"👉 Account Username : imad.ghobrini")
        print(f"👉 Account Password : Imad2026!Pass")
        print(f"👉 Resident ID      : {imad_elderly.id}")
        print(f"👉 Device UID       : {imad_device.device_uid}")
        print(f"👉 Critical Alert ID: {fall_alert.id}")


if __name__ == "__main__":
    asyncio.run(seed_imad_data())
