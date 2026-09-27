import { apiRequest } from './client';
import { AdminStats, User, UserRole } from '../types';

export const adminApi = {
  getUsers: async (skip = 0, limit = 50, role?: UserRole): Promise<{ items: User[]; total: number }> => {
    let url = `/api/v1/admin/users?skip=${skip}&limit=${limit}`;
    if (role) url += `&role=${role}`;
    return apiRequest<{ items: User[]; total: number }>(url);
  },

  createUser: async (data: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
    role: UserRole;
    assigned_elderly_ids?: string[];
  }): Promise<User> => {
    return apiRequest<User>('/api/v1/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  updateUser: async (id: string, data: Partial<{
    username: string;
    email: string;
    password?: string;
    full_name: string;
    role: UserRole;
    is_active: boolean;
    assigned_elderly_ids: string[];
  }>): Promise<User> => {
    return apiRequest<User>(`/api/v1/admin/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  deleteUser: async (id: string): Promise<void> => {
    return apiRequest<void>(`/api/v1/admin/users/${id}`, {
      method: 'DELETE',
    });
  },

  getStats: async (): Promise<AdminStats> => {
    return apiRequest<AdminStats>('/api/v1/admin/stats');
  },

  getRbacMatrix: async (): Promise<import('../types').RbacMatrixResponse> => {
    return apiRequest<import('../types').RbacMatrixResponse>('/api/v1/admin/rbac/matrix');
  },
};
