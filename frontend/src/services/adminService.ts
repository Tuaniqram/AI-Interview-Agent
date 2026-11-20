import { apiClient } from './apiClient';
import type { PlatformStats, AdminOrg, AdminUser } from '../types/admin';

export const adminService = {
  async getStats(): Promise<PlatformStats> {
    return apiClient.get<PlatformStats>('/api/v1/admin/stats');
  },

  async listOrganizations(search?: string): Promise<AdminOrg[]> {
    const params = search ? { search } : {};
    return apiClient.get<AdminOrg[]>('/api/v1/admin/organizations', { params });
  },

  async toggleSuspend(orgId: string): Promise<void> {
    await apiClient.post(`/api/v1/admin/organizations/${orgId}/toggle-suspend`);
  },

  async listUsers(search?: string): Promise<AdminUser[]> {
    const params = search ? { search } : {};
    return apiClient.get<AdminUser[]>('/api/v1/admin/users', { params });
  },
};
