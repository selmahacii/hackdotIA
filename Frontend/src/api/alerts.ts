import { apiRequest } from './client';
import { Alert, AlertSeverity, AlertStatus, AlertType, AIAnalysis } from '../types';

export const alertsApi = {
  list: async (filters: {
    elderlyId?: string;
    severity?: AlertSeverity;
    status?: AlertStatus;
    alertType?: AlertType;
    skip?: number;
    limit?: number;
  } = {}): Promise<{ items: Alert[]; total: number; skip: number; limit: number }> => {
    const params = new URLSearchParams();
    if (filters.elderlyId) params.append('elderly_id', filters.elderlyId);
    if (filters.severity) params.append('severity', filters.severity);
    if (filters.status) params.append('alert_status', filters.status);
    if (filters.alertType) params.append('alert_type', filters.alertType);
    if (filters.skip !== undefined) params.append('skip', String(filters.skip));
    if (filters.limit !== undefined) params.append('limit', String(filters.limit));

    const qs = params.toString();
    return apiRequest<{ items: Alert[]; total: number; skip: number; limit: number }>(
      `/api/v1/alerts${qs ? `?${qs}` : ''}`
    );
  },

  getById: async (id: string): Promise<Alert> => {
    return apiRequest<Alert>(`/api/v1/alerts/${id}`);
  },

  ack: async (id: string): Promise<{ id: string; status: AlertStatus; acknowledged_at: string; acknowledged_by: string }> => {
    return apiRequest(`/api/v1/alerts/${id}/ack`, {
      method: 'POST',
    });
  },

  resolve: async (id: string): Promise<{ id: string; status: AlertStatus; resolved_at: string }> => {
    return apiRequest(`/api/v1/alerts/${id}/resolve`, {
      method: 'POST',
    });
  },

  triggerAi: async (id: string, force = false): Promise<AIAnalysis> => {
    return apiRequest<AIAnalysis>(`/api/v1/alerts/${id}/ai-analyses?force=${force}`, {
      method: 'POST',
    });
  },
};
