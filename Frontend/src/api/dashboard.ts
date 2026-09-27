import { apiRequest } from './client';
import { DashboardStats } from '../types';

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    return apiRequest<DashboardStats>('/api/v1/dashboard/stats');
  },
};
