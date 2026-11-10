import { apiClient } from './apiClient';

export interface OverviewData {
  total_it_roles: number;
  total_sessions: number;
  active_sessions: number;
  completed_sessions: number;
  average_score: number | null;
  completion_rate: number;
}

export interface TrendPoint {
  date: string;
  avg_score: number;
  count: number;
}

export interface DistributionPoint {
  range: string;
  count: number;
}

export interface ItRoleData {
  it_role_id: string;
  name: string;
  session_count: number;
  avg_score: number | null;
}

export interface RoleData {
  job_role: string;
  count: number;
  avg_score: number | null;
}

export const analyticsService = {
  async getOverview(): Promise<OverviewData> {
    return apiClient.get<OverviewData>('/api/v1/analytics/overview');
  },

  async getScoreTrend(): Promise<TrendPoint[]> {
    return apiClient.get<TrendPoint[]>('/api/v1/analytics/scores/trend');
  },

  async getScoreDistribution(): Promise<DistributionPoint[]> {
    return apiClient.get<DistributionPoint[]>('/api/v1/analytics/scores/distribution');
  },

  async getSessionsByItRole(): Promise<ItRoleData[]> {
    return apiClient.get<ItRoleData[]>('/api/v1/analytics/sessions/by-it-role');
  },

  async getSessionsByRole(): Promise<RoleData[]> {
    return apiClient.get<RoleData[]>('/api/v1/analytics/sessions/by-role');
  },
};
