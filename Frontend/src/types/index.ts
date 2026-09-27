export type UserRole = 'SUPERADMIN' | 'ADMIN' | 'CAREGIVER' | 'OPERATOR' | 'READ_ONLY';

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  assigned_elderly_ids: string[];
  created_at?: string;
  updated_at?: string;
  last_login_at?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface ElderlyPerson {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string | null;
  phone: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type DeviceStatus = 'ONLINE' | 'OFFLINE' | 'UNKNOWN';

export interface Device {
  id: string;
  elderly_id: string;
  device_uid: string;
  name: string | null;
  status: DeviceStatus;
  firmware_version: string | null;
  battery_level: number | null;
  wifi_rssi: number | null;
  capabilities: Record<string, any> | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export type AlertType =
  | 'FALL_SUSPECTED'
  | 'HEART_RATE_ANOMALY'
  | 'SPO2_ANOMALY'
  | 'TEMPERATURE_ANOMALY'
  | 'SENSOR_HEALTH'
  | 'DEVICE_OFFLINE'
  | 'GPS_UNAVAILABLE';

export type AlertSeverity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
export type AlertSource = 'RULE_ENGINE' | 'SENSOR_HEALTH' | 'DEVICE' | 'SYSTEM';
export type AIProvider = 'GROQ' | 'NVIDIA' | 'FALLBACK_RULES' | 'NONE';
export type AIAnalysisStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'FALLBACK';

export interface AIAnalysis {
  id: string;
  provider: AIProvider;
  status: AIAnalysisStatus;
  risk_level: string;
  anomaly_detected: boolean;
  possible_event: string;
  explanation: string;
  recommended_action: string;
  confidence: number;
  model_name: string | null;
  latency_ms: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface Alert {
  id: string;
  elderly_id: string;
  elderly_name?: string | null;
  device_id: string | null;
  device_uid?: string | null;
  device_name?: string | null;
  alert_type: AlertType;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  description: string;
  source: AlertSource;
  occurred_at: string;
  occurrence_count: number;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved_at: string | null;
  context?: Record<string, any> | null;
  has_ai_analysis?: boolean;
  ai_status?: AIAnalysisStatus | null;
  ai_summary?: string | null;
  ai_analyses?: AIAnalysis[];
}

export interface Measurement {
  id: string;
  event_id?: string | null;
  device_id: string;
  elderly_id: string;
  measured_at: string;
  received_at?: string;
  bpm: number | null;
  spo2: number | null;
  finger_detected: boolean;
  temperature_c: number | null;
  humidity_percent: number | null;
  accel_x_g: number | null;
  accel_y_g: number | null;
  accel_z_g: number | null;
  accel_magnitude_g: number | null;
  gps_latitude: number | null;
  gps_longitude: number | null;
  gps_fix_valid: boolean;
  battery_level: number | null;
  wifi_rssi: number | null;
}

export interface MeasurementHistoryPoint {
  timestamp: string;
  bpm: number | null;
  spo2: number | null;
  temperature_c: number | null;
  humidity_percent: number | null;
  accel_magnitude_g: number | null;
  battery_level: number | null;
  finger_detected: boolean;
}

export type SensorStatus = 'HEALTHY' | 'NO_CONTACT' | 'SUSPECT' | 'UNAVAILABLE' | 'UNKNOWN';

export interface SensorHealthRecord {
  device_id: string;
  device_uid: string;
  device_name: string | null;
  device_status: DeviceStatus;
  elderly_id: string;
  elderly_name: string;
  last_checked_at: string | null;
  max30102_status: SensorStatus;
  mpu6050_status: SensorStatus;
  dht11_status: SensorStatus;
  gps_status: SensorStatus;
  details?: Record<string, any>;
}

export interface DashboardStats {
  kpi: {
    residents_count: number;
    devices_total: number;
    devices_online: number;
    devices_offline: number;
    open_alerts_total: number;
    critical_alerts: number;
    high_alerts: number;
    medium_alerts: number;
    low_alerts: number;
  };
  recent_alerts: {
    id: string;
    elderly_name: string;
    title: string;
    severity: AlertSeverity;
    status: AlertStatus;
    occurred_at: string;
    has_ai: boolean;
  }[];
  recent_measurements: {
    id: string;
    measured_at: string;
    bpm: number | null;
    spo2: number | null;
    temperature_c: number | null;
    accel_magnitude_g: number | null;
  }[];
  ai_engine: {
    groq_enabled: boolean;
    groq_model: string | null;
    status: string;
  };
}

export interface AdminStats {
  users: {
    total: number;
    by_role: Record<string, number>;
  };
  residents: number;
  devices: {
    total: number;
    online: number;
    offline: number;
  };
  alerts: {
    open: number;
  };
  measurements: {
    total: number;
  };
  system_status: string;
}

export interface RbacRoleMetadata {
  role: UserRole;
  name: string;
  level: number;
  badge_variant: string;
  description: string;
  target_persona: string;
  caregiver_isolation: boolean;
  can_delete_users: boolean;
  can_manage_admins: boolean;
}

export interface RbacPermission {
  code: string;
  label: string;
  description: string;
  roles: UserRole[];
}

export interface RbacModule {
  category: string;
  permissions: RbacPermission[];
}

export interface RbacPolicies {
  caregiver_isolation_mode: string;
  caregiver_scope_rule: string;
  token_algorithm: string;
  token_ttl_minutes: number;
  least_privilege_enforced: boolean;
}

export interface RbacMatrixResponse {
  roles: RbacRoleMetadata[];
  modules: RbacModule[];
  policies: RbacPolicies;
}

export interface AIChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface AIChatRequest {
  message: string;
  elderly_id?: string | null;
  alert_id?: string | null;
  history?: AIChatMessage[];
}

export interface AIChatResponse {
  reply: string;
  context_used: Record<string, any>;
  model_name: string | null;
  latency_ms: number | null;
}

