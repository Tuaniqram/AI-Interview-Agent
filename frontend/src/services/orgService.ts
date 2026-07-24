import { apiClient } from './apiClient';
import type { Organization, OrgMember, OrganizationCreate, OrganizationUpdate } from '../types/org';

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

  async listMembers(orgId: string): Promise<OrgMember[]> {
    return apiClient.get<OrgMember[]>(`/api/v1/orgs/${orgId}/members`);
  },

  async addMember(orgId: string, userId: string, role: string = 'member'): Promise<OrgMember> {
    return apiClient.post<OrgMember>(`/api/v1/orgs/${orgId}/members`, { user_id: userId, role });
  },

  async updateMemberRole(orgId: string, memberId: string, role: string): Promise<OrgMember> {
    return apiClient.patch<OrgMember>(`/api/v1/orgs/${orgId}/members/${memberId}`, { role });
  },

  async removeMember(orgId: string, memberId: string): Promise<void> {
    await apiClient.delete(`/api/v1/orgs/${orgId}/members/${memberId}`);
  },
};
