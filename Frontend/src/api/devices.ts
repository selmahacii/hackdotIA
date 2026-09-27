import { apiRequest } from './client';
import { Device, DeviceStatus } from '../types';

export const devicesApi = {
  list: async (elderlyId?: string, status?: DeviceStatus): Promise<Device[]> => {
    let url = '/api/v1/devices?';
    if (elderlyId) url += `elderly_id=${elderlyId}&`;
    if (status) url += `device_status=${status}&`;
    return apiRequest<Device[]>(url);
  },

  getById: async (id: string): Promise<Device> => {
    return apiRequest<Device>(`/api/v1/devices/${id}`);
  },

  create: async (data: {
    device_uid: string;
    elderly_id: string;
    name?: string;
    firmware_version?: string;
  }): Promise<Device> => {
    return apiRequest<Device>('/api/v1/devices', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: Partial<Device>): Promise<Device> => {
    return apiRequest<Device>(`/api/v1/devices/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string): Promise<void> => {
    return apiRequest<void>(`/api/v1/devices/${id}`, {
      method: 'DELETE',
    });
  },
};
