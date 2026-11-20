import { apiClient } from './apiClient';

export interface ItRole {
  id: string;
  slug: string;
  family: string;
  name: string;
  description?: string | null;
  level_min: string;
  level_max: string;
  is_active: boolean;
}

export interface ItCompetency {
  id: string;
  name: string;
  category: string;
  primary_dimension: string;
  evidence_dimensions: string[];
  default_min_evidence: number;
  scope: string;
}

export interface ItRoleCompetency {
  competency_id: string;
  name: string;
  category: string;
  primary_dimension: string;
  weight: number | null;
  required_level: string | null;
  is_core: boolean;
}

export const itService = {
  async listRoles(params?: { family?: string; active_only?: boolean }): Promise<ItRole[]> {
    return apiClient.get<ItRole[]>('/api/v1/it/roles', params);
  },

  async getRole(slug: string): Promise<ItRole> {
    return apiClient.get<ItRole>(`/api/v1/it/roles/${slug}`);
  },

  async getRoleCompetencies(slug: string): Promise<ItRoleCompetency[]> {
    return apiClient.get<ItRoleCompetency[]>(`/api/v1/it/roles/${slug}/competencies`);
  },

  async listCompetencies(params?: { category?: string }): Promise<ItCompetency[]> {
    return apiClient.get<ItCompetency[]>('/api/v1/it/competencies', params);
  },
};
