export interface OrgListing {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  website: string | null;
  logo_url: string | null;
  interview_count: number;
}

export interface PublicInterview {
  id: string;
  org_id: string;
  title: string;
  description: string | null;
  rich_description: string | null;
  interview_mode: string;
  org_name: string | null;
  department_name: string | null;
  skills_required: string | null;
  starts_at: string | null;
  expires_at: string | null;
}

export interface OrgPublicListing {
  id: string;
  org_id: string;
  department_id: number | null;
  department_name: string | null;
  title: string;
  description: string | null;
  rich_description: string | null;
  interview_mode: string;
  is_open: boolean;
  token: string;
  max_candidates: number | null;
  token_expires_at: string | null;
  skills_required: string | null;
  starts_at: string | null;
  expires_at: string | null;
  created_at: string | null;
}

export interface CreateListingRequest {
  title: string;
  department_id: number;
  description?: string;
  interview_mode?: string;
  max_candidates?: number;
  skills_required?: string;
  starts_at?: string;
  expires_at?: string;
}

export interface UpdateListingRequest {
  title?: string;
  department_id?: number;
  description?: string;
  interview_mode?: string;
  is_open?: boolean;
  max_candidates?: number;
  skills_required?: string;
  starts_at?: string;
  expires_at?: string;
}

export interface StartInterviewRequest {
  candidate_email: string;
  candidate_name: string;
}

export interface StartInterviewResponse {
  session_id: string;
  token: string;
}
