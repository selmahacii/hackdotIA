import { apiRequest } from './client';
import { SensorHealthRecord } from '../types';

export const sensorsApi = {
  list: async (deviceId?: string): Promise<SensorHealthRecord[]> => {
    const url = deviceId ? `/api/v1/sensors?device_id=${deviceId}` : '/api/v1/sensors';
    return apiRequest<SensorHealthRecord[]>(url);
  },
};
