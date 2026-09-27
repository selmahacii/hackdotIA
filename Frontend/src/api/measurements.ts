import { apiRequest } from './client';
import { Measurement, MeasurementHistoryPoint } from '../types';

export const measurementsApi = {
  list: async (filters: {
    elderlyId?: string;
    deviceId?: string;
    skip?: number;
    limit?: number;
  } = {}): Promise<Measurement[]> => {
    const params = new URLSearchParams();
    if (filters.elderlyId) params.append('elderly_id', filters.elderlyId);
    if (filters.deviceId) params.append('device_id', filters.deviceId);
    if (filters.skip !== undefined) params.append('skip', String(filters.skip));
    if (filters.limit !== undefined) params.append('limit', String(filters.limit));

    const qs = params.toString();
    return apiRequest<Measurement[]>(`/api/v1/measurements${qs ? `?${qs}` : ''}`);
  },

  getLatest: async (params: { elderlyId?: string; deviceId?: string }): Promise<Measurement | null> => {
    const query = new URLSearchParams();
    if (params.elderlyId) query.append('elderly_id', params.elderlyId);
    if (params.deviceId) query.append('device_id', params.deviceId);
    return apiRequest<Measurement | null>(`/api/v1/measurements/latest?${query.toString()}`);
  },

  getHistory: async (elderlyId: string, limit = 60): Promise<MeasurementHistoryPoint[]> => {
    return apiRequest<MeasurementHistoryPoint[]>(
      `/api/v1/measurements/history?elderly_id=${elderlyId}&limit=${limit}`
    );
  },
};
