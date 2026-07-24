export interface CandidateProfile {
  id: string;
  email: string;
  name: string;
  phone: string | null;
  resume_url: string | null;
  is_registered: boolean;
  is_verified: boolean;
  skills: string | null;
  created_at: string | null;
}

export interface CandidateTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CandidateAuthResponse {
  candidate: CandidateProfile;
  tokens: CandidateTokens;
}

export interface CandidateLoginRequest {
  email: string;
  password: string;
}

export interface CandidateRegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface CandidateUpdateRequest {
  name?: string;
  phone?: string;
  resume_url?: string;
  skills?: string;
}

export interface CandidateInterview {
  id: string;
  job_role: string;
  session_type: string;
  interaction_mode: string | null;
  status: string | null;
  final_score: number | null;
  started_at: string | null;
  ended_at: string | null;
  department_name: string | null;
}

export interface CandidateInterviewDetail {
  id: string;
  job_role: string;
  session_type: string;
  interaction_mode: string | null;
  status: string | null;
  final_score: number | null;
  final_feedback: string | null;
  started_at: string | null;
  ended_at: string | null;
  department_name: string | null;
  department_id: number | null;
}

export interface CandidateStats {
  total_interviews: number;
  completed_interviews: number;
  active_interviews: number;
  average_score: number | null;
}

export interface PracticeStartRequest {
  job_role: string;
  difficulty: string;
  tech_stack?: string;
  num_questions: number;
}

export interface PracticeStartResponse {
  session_id: string;
  job_role: string;
  total_questions: number;
}
