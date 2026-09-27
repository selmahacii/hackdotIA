import { apiRequest } from './client';
import { ElderlyPerson } from '../types';

export const elderlyApi = {
  list: async (activeOnly = true, skip = 0, limit = 100, search?: string): Promise<ElderlyPerson[]> => {
    const params = new URLSearchParams({
      active_only: String(activeOnly),
      skip: String(skip),
      limit: String(limit),
    });
    if (search) params.append('search', search);
    return apiRequest<ElderlyPerson[]>(`/api/v1/elderly?${params.toString()}`);
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
