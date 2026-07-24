import { apiClient } from './apiClient';
import type {
  CandidateAuthResponse,
  CandidateLoginRequest,
  CandidateRegisterRequest,
  CandidateTokens,
  CandidateUpdateRequest,
  CandidateProfile,
  CandidateInterview,
  CandidateInterviewDetail,
  CandidateStats,
  PracticeStartRequest,
  PracticeStartResponse,
} from '../types/candidate';

export const candidateService = {
  async register(data: CandidateRegisterRequest): Promise<CandidateAuthResponse> {
    return apiClient.post<CandidateAuthResponse>('/api/v1/candidates/register', data);
  },

  async login(data: CandidateLoginRequest): Promise<CandidateAuthResponse> {
    return apiClient.post<CandidateAuthResponse>('/api/v1/candidates/login', data);
  },

  async googleLogin(credential: string): Promise<CandidateAuthResponse> {
    return apiClient.post<CandidateAuthResponse>('/api/v1/candidates/google', { credential });
  },

  async refresh(refreshToken: string): Promise<CandidateTokens> {
    return apiClient.post<CandidateTokens>('/api/v1/candidates/refresh', { refresh_token: refreshToken });
  },

  async me(): Promise<CandidateProfile> {
    return apiClient.get<CandidateProfile>('/api/v1/candidates/me');
  },

  async updateProfile(data: CandidateUpdateRequest): Promise<CandidateProfile> {
    return apiClient.patch<CandidateProfile>('/api/v1/candidates/me', data);
  },

  async getInterviews(): Promise<CandidateInterview[]> {
    return apiClient.get<CandidateInterview[]>('/api/v1/candidates/interviews');
  },

  async getInterviewDetail(interviewId: string): Promise<CandidateInterviewDetail> {
    return apiClient.get<CandidateInterviewDetail>(`/api/v1/candidates/interviews/${interviewId}`);
  },

  async getStats(): Promise<CandidateStats> {
    return apiClient.get<CandidateStats>('/api/v1/candidates/stats');
  },

  async startPractice(data: PracticeStartRequest): Promise<PracticeStartResponse> {
    return apiClient.post<PracticeStartResponse>('/api/v1/candidates/practice/start', data);
  },
};
