import { apiClient } from './apiClient';
import type { ScorecardTemplate, ScorecardResult } from '../types/scorecard';

export const scorecardService = {
  async list(orgId: string): Promise<ScorecardTemplate[]> {
    return apiClient.get<ScorecardTemplate[]>(`/api/v1/orgs/${orgId}/scorecards`);
  },

  async get(orgId: string, templateId: string): Promise<ScorecardTemplate> {
    return apiClient.get<ScorecardTemplate>(`/api/v1/orgs/${orgId}/scorecards/${templateId}`);
  },

  async create(orgId: string, data: { name: string; competencies: any[] }): Promise<ScorecardTemplate> {
    return apiClient.post<ScorecardTemplate>(`/api/v1/orgs/${orgId}/scorecards`, data);
  },

  async update(orgId: string, templateId: string, data: { name?: string; competencies?: any[] }): Promise<ScorecardTemplate> {
    return apiClient.put<ScorecardTemplate>(`/api/v1/orgs/${orgId}/scorecards/${templateId}`, data);
  },

  async delete(orgId: string, templateId: string): Promise<void> {
    await apiClient.delete(`/api/v1/orgs/${orgId}/scorecards/${templateId}`);
  },

  async calculate(orgId: string, templateId: string, sessionId: string): Promise<ScorecardResult> {
    return apiClient.post<ScorecardResult>(`/api/v1/orgs/${orgId}/scorecards/${templateId}/sessions/${sessionId}/calculate`);
  },

  async getSessionResult(orgId: string, sessionId: string): Promise<ScorecardResult | null> {
    return apiClient.get<ScorecardResult | null>(`/api/v1/orgs/${orgId}/scorecards/sessions/${sessionId}`);
  },
};
