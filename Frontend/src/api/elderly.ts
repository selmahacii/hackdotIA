import { apiRequest } from './client';
import { ElderlyPerson } from '../types';

export const elderlyApi = {
  list: async (activeOnly = true, skip = 0, limit = 50): Promise<ElderlyPerson[]> => {
    return apiRequest<ElderlyPerson[]>(
      `/api/v1/elderly?active_only=${activeOnly}&skip=${skip}&limit=${limit}`
    );
  },

  getById: async (id: string): Promise<ElderlyPerson> => {
    return apiRequest<ElderlyPerson>(`/api/v1/elderly/${id}`);
  },

  create: async (data: Partial<ElderlyPerson>): Promise<ElderlyPerson> => {
    return apiRequest<ElderlyPerson>('/api/v1/elderly', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: Partial<ElderlyPerson>): Promise<ElderlyPerson> => {
    return apiRequest<ElderlyPerson>(`/api/v1/elderly/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string): Promise<void> => {
    return apiRequest<void>(`/api/v1/elderly/${id}`, {
      method: 'DELETE',
    });
  },
};
