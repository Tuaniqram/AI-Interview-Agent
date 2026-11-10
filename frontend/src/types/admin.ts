export interface PlatformStats {
  total_orgs: number;
  total_users: number;
  total_interviews: number;
  active_sessions: number;
}

export interface AdminOrg {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  owner_name: string | null;
  owner_email: string | null;
  interview_count: number;
  created_at: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  is_admin: boolean;
  org_name: string | null;
  created_at: string | null;
}
