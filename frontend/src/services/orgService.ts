import { apiClient } from './apiClient';
import type { Organization, OrganizationCreate, OrganizationUpdate } from '../types/org';

export const orgService = {
  async create(data: OrganizationCreate): Promise<Organization> {
    return apiClient.post<Organization>('/api/v1/orgs', data);
  },

  async get(orgId: string): Promise<Organization> {
    return apiClient.get<Organization>(`/api/v1/orgs/${orgId}`);
  },

  async update(orgId: string, data: OrganizationUpdate): Promise<Organization> {
    return apiClient.patch<Organization>(`/api/v1/orgs/${orgId}`, data);
  },
};
