export interface PlatformStats {
  total_orgs: number;
  total_users: number;
  total_interviews: number;
  total_departments: number;
  active_sessions: number;
}

export interface AdminOrg {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  member_count: number;
  interview_count: number;
  created_at: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string | null;
}
