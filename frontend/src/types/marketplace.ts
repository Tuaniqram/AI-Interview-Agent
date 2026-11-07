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
  it_role_id: string | null;
  title: string;
  description: string | null;
  rich_description: string | null;
  interview_mode: string;
  org_name: string | null;
  department_name: string | null;
  skills_required: string | null;
  style_name: string | null;
  starts_at: string | null;
  expires_at: string | null;
}

export interface OrgPublicListing {
  id: string;
  org_id: string;
  it_role_id: string;
  level_code: string | null;
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
  style_name: string | null;
  template_id: string | null;
  starts_at: string | null;
  expires_at: string | null;
  created_at: string | null;
}

export interface CreateListingRequest {
  title: string;
  it_role_id: string;
  level_code?: string;
  description?: string;
  interview_mode?: string;
  max_candidates?: number;
  skills_required?: string;
  style_name?: string;
  template_id?: string;
  starts_at?: string;
  expires_at?: string;
}

export interface UpdateListingRequest {
  title?: string;
  it_role_id?: string;
  level_code?: string;
  description?: string;
  interview_mode?: string;
  is_open?: boolean;
  max_candidates?: number;
  skills_required?: string;
  style_name?: string;
  template_id?: string;
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

/** Sent as multipart/form-data. Guests need email + name + resume; logged-in candidates may omit all three when their profile already has a CV. */
export interface ApplyRequest {
  candidate_email?: string;
  candidate_name?: string;
  resume_document_id?: string;
  resume?: File;
}

export type FitStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface FitCompetencyMatch {
  id: string;
  name: string;
  /** Present on matched competencies: what in the CV shows it. */
  evidence?: string;
  /** Present on missing competencies: why the CV does not show it. */
  reason?: string;
}

/** Structured output of the automatic application fit evaluation. */
export interface FitBreakdown {
  matched_competencies: FitCompetencyMatch[];
  missing_competencies: FitCompetencyMatch[];
  resume_strengths: string[];
  risks: string[];
  recommended_probes: string[];
  meta?: {
    org_documents_used?: number;
    competencies_considered?: number;
    [key: string]: unknown;
  };
}

export interface Application {
  id: string;
  public_id: string;
  public_title: string | null;
  org_name: string | null;
  session_id: string | null;
  candidate_profile_id: string | null;
  resume_document_id: string | null;
  candidate_email: string;
  candidate_name: string;
  status: string;
  fit_score: number | null;
  fit_summary: string | null;
  fit_status: FitStatus;
  fit_breakdown: FitBreakdown | null;
  fit_evaluated_at: string | null;
  has_resume: boolean;
  resume_filename: string | null;
  org_decision: string;
  candidate_response: string;
  outcome: string;
  invited_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** Public invitation page payload (GET /marketplace/application-invitations/{token}). */
export interface ApplicationInvitation {
  org_name: string | null;
  job_title: string;
  candidate_name: string;
  candidate_email: string;
  status: string;
  candidate_response: string;
  can_respond: boolean;
  expired: boolean;
  expires_at: string | null;
  /** Only present after the invitation was accepted. */
  session_id: string | null;
  /** Lets an account-less guest open that one interview session. */
  access_token: string | null;
}

export interface FitScoreRequest {
  fit_score: number;
  fit_summary?: string;
}

export interface CandidateResponseRequest {
  response: string;
}

export interface ApplicationOutcomeRequest {
  outcome: string;
}
