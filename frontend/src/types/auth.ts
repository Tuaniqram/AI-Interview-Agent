export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  is_admin: boolean;
  is_active: boolean;
  created_at: string | null;
}

export interface OrgMembership {
  org_id: string;
  org_name: string;
  org_slug: string;
  role: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthState {
  user: User | null;
  tokens: Tokens | null;
  memberships: OrgMembership[];
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  org_name: string;
}

export interface AuthResponse {
  user: User;
  tokens: Tokens;
  memberships: OrgMembership[];
}

export interface MeResponse {
  user: User;
  memberships: OrgMembership[];
}
