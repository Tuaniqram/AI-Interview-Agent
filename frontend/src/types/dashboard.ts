export interface DashboardMetrics {
  totalCompanies: number;
  totalSessions: number;
  activeSessions: number;
  averageScore: number | null;
}

export interface RecentSessionSummary {
  session_id: string;
  candidate_id?: string;
  job_role: string;
  status: string;
  final_score: number | null;
  started_at: string;
  company_name?: string;
}
