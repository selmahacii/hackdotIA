"""create_initial_domain_tables

Revision ID: 9b3154de6499
Revises: 
Create Date: 2026-09-27 11:15:03.715544

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9b3154de6499'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('elderly_person',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('date_of_birth', sa.Date(), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('emergency_contact_name', sa.String(length=150), nullable=True),
    sa.Column('emergency_contact_phone', sa.String(length=50), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('device',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('device_uid', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('elderly_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('ONLINE', 'OFFLINE', 'UNKNOWN', name='device_status_enum'), nullable=False),
    sa.Column('firmware_version', sa.String(length=50), nullable=True),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('battery_level', sa.Float(), nullable=True),
    sa.Column('wifi_rssi', sa.Integer(), nullable=True),
    sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['elderly_id'], ['elderly_person.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_device_uid'), 'device', ['device_uid'], unique=True)
    op.create_index(op.f('ix_device_elderly_id'), 'device', ['elderly_id'], unique=False)
    op.create_index('ix_device_elderly_status', 'device', ['elderly_id', 'status'], unique=False)
    op.create_table('alert',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('elderly_id', sa.UUID(), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=True),
    sa.Column('alert_type', sa.Enum('FALL_SUSPECTED', 'HEART_RATE_ANOMALY', 'SPO2_ANOMALY', 'TEMPERATURE_ANOMALY', 'SENSOR_HEALTH', 'DEVICE_OFFLINE', 'GPS_UNAVAILABLE', name='alert_type_enum'), nullable=False),
    sa.Column('severity', sa.Enum('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='alert_severity_enum'), nullable=False),
    sa.Column('status', sa.Enum('OPEN', 'ACKNOWLEDGED', 'RESOLVED', name='alert_status_enum'), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=1000), nullable=False),
    sa.Column('source', sa.Enum('RULE_ENGINE', 'SENSOR_HEALTH', 'DEVICE', 'SYSTEM', name='alert_source_enum'), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('occurrence_count', sa.Integer(), nullable=False),
    sa.Column('dedup_key', sa.String(length=255), nullable=False),
    sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['elderly_id'], ['elderly_person.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_dedup_key'), 'alert', ['dedup_key'], unique=False)
    op.create_index('ix_alert_dedup_status', 'alert', ['dedup_key', 'status'], unique=False)
    op.create_index(op.f('ix_alert_device_id'), 'alert', ['device_id'], unique=False)
    op.create_index('ix_alert_elderly_created_at', 'alert', ['elderly_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_alert_elderly_id'), 'alert', ['elderly_id'], unique=False)
    op.create_index('ix_alert_elderly_status', 'alert', ['elderly_id', 'status'], unique=False)
    op.create_index('ix_alert_type_status', 'alert', ['alert_type', 'status'], unique=False)
    op.create_index('uq_alert_active_dedup_key', 'alert', ['dedup_key'], unique=True, postgresql_where=sa.text("status IN ('OPEN', 'ACKNOWLEDGED')"))
    op.create_table('measurement',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('elderly_id', sa.UUID(), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('bpm', sa.Float(), nullable=True),
    sa.Column('spo2', sa.Float(), nullable=True),
    sa.Column('finger_detected', sa.Boolean(), nullable=False),
    sa.Column('temperature_c', sa.Float(), nullable=True),
    sa.Column('humidity_percent', sa.Float(), nullable=True),
    sa.Column('accel_x_g', sa.Float(), nullable=True),
    sa.Column('accel_y_g', sa.Float(), nullable=True),
    sa.Column('accel_z_g', sa.Float(), nullable=True),
    sa.Column('accel_magnitude_g', sa.Float(), nullable=True),
    sa.Column('gps_latitude', sa.Float(), nullable=True),
    sa.Column('gps_longitude', sa.Float(), nullable=True),
    sa.Column('gps_fix_valid', sa.Boolean(), nullable=False),
    sa.Column('battery_level', sa.Float(), nullable=True),
    sa.Column('wifi_rssi', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['elderly_id'], ['elderly_person.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_measurement_device_id'), 'measurement', ['device_id'], unique=False)
    op.create_index('ix_measurement_device_measured_at', 'measurement', ['device_id', 'measured_at'], unique=False)
    op.create_index(op.f('ix_measurement_elderly_id'), 'measurement', ['elderly_id'], unique=False)
    op.create_index('ix_measurement_elderly_measured_at', 'measurement', ['elderly_id', 'measured_at'], unique=False)
    op.create_table('ai_analysis',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('alert_id', sa.UUID(), nullable=False),
    sa.Column('provider', sa.Enum('NVIDIA', 'FALLBACK_RULES', 'NONE', name='ai_provider_enum'), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'FALLBACK', name='ai_analysis_status_enum'), nullable=False),
    sa.Column('risk_level', sa.String(length=50), nullable=True),
    sa.Column('anomaly_detected', sa.Boolean(), nullable=True),
    sa.Column('possible_event', sa.String(length=100), nullable=True),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('recommended_action', sa.Text(), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('model_name', sa.String(length=100), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['alert_id'], ['alert.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_analysis_alert_id'), 'ai_analysis', ['alert_id'], unique=False)
    op.create_table('sensor_health',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('measurement_id', sa.UUID(), nullable=False),
    sa.Column('device_id', sa.UUID(), nullable=False),
    sa.Column('max30102_status', sa.Enum('HEALTHY', 'NO_CONTACT', 'SUSPECT', 'UNAVAILABLE', 'UNKNOWN', name='sensor_health_status_enum'), nullable=False),
    sa.Column('dht11_status', sa.Enum('HEALTHY', 'NO_CONTACT', 'SUSPECT', 'UNAVAILABLE', 'UNKNOWN', name='sensor_health_status_enum'), nullable=False),
    sa.Column('mpu6050_status', sa.Enum('HEALTHY', 'NO_CONTACT', 'SUSPECT', 'UNAVAILABLE', 'UNKNOWN', name='sensor_health_status_enum'), nullable=False),
    sa.Column('gps_status', sa.Enum('HEALTHY', 'NO_CONTACT', 'SUSPECT', 'UNAVAILABLE', 'UNKNOWN', name='sensor_health_status_enum'), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['device.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['measurement_id'], ['measurement.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('measurement_id')
    )
    op.create_index(op.f('ix_sensor_health_device_id'), 'sensor_health', ['device_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_sensor_health_device_id'), table_name='sensor_health')
    op.drop_table('sensor_health')
    op.drop_index(op.f('ix_ai_analysis_alert_id'), table_name='ai_analysis')
    op.drop_table('ai_analysis')
    op.drop_index('ix_measurement_elderly_measured_at', table_name='measurement')
    op.drop_index(op.f('ix_measurement_elderly_id'), table_name='measurement')
    op.drop_index('ix_measurement_device_measured_at', table_name='measurement')
    op.drop_index(op.f('ix_measurement_device_id'), table_name='measurement')
    op.drop_table('measurement')
    op.drop_index('uq_alert_active_dedup_key', table_name='alert', postgresql_where=sa.text("status IN ('OPEN', 'ACKNOWLEDGED')"))
    op.drop_index('ix_alert_type_status', table_name='alert')
    op.drop_index('ix_alert_elderly_status', table_name='alert')
    op.drop_index(op.f('ix_alert_elderly_id'), table_name='alert')
    op.drop_index('ix_alert_elderly_created_at', table_name='alert')
    op.drop_index(op.f('ix_alert_device_id'), table_name='alert')
    op.drop_index('ix_alert_dedup_status', table_name='alert')
    op.drop_index(op.f('ix_alert_dedup_key'), table_name='alert')
    op.drop_table('alert')
    op.drop_index('ix_device_elderly_status', table_name='device')
    op.drop_index(op.f('ix_device_elderly_id'), table_name='device')
    op.drop_index(op.f('ix_device_device_uid'), table_name='device')
    op.drop_table('device')
    op.drop_table('elderly_person')
    
    # Drop PostgreSQL native ENUM types cleanly
    sa.Enum(name='sensor_health_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='ai_analysis_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='ai_provider_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='alert_source_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='alert_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='alert_severity_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='alert_type_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='device_status_enum').drop(op.get_bind(), checkfirst=True)
    # ### end Alembic commands ###
 #c'est genere par alem bic dont ca doit etre ajustable avec le temps 