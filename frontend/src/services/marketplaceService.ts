import { apiClient } from './apiClient';
import type {
  OrgListing,
  PublicInterview,
  OrgPublicListing,
  CreateListingRequest,
  UpdateListingRequest,
  StartInterviewRequest,
  StartInterviewResponse,
  ApplyRequest,
  Application,
  FitScoreRequest,
  CandidateResponseRequest,
  ApplicationOutcomeRequest,
} from '../types/marketplace';

export const marketplaceService = {
  async listOrganizations(params?: { search?: string; modes?: string; expiry?: string }): Promise<OrgListing[]> {
    return apiClient.get<OrgListing[]>('/api/v1/marketplace/organizations', params);
  },

  async getOrgProfile(slug: string): Promise<{ org: OrgListing; interviews: PublicInterview[] }> {
    return apiClient.get<{ org: OrgListing; interviews: PublicInterview[] }>(
      `/api/v1/marketplace/organizations/${slug}`
    );
  },

  async getInterview(interviewId: string): Promise<PublicInterview> {
    return apiClient.get<PublicInterview>(`/api/v1/marketplace/interviews/${interviewId}`);
  },

  async startInterview(interviewId: string, data: StartInterviewRequest): Promise<StartInterviewResponse> {
    return apiClient.post<StartInterviewResponse>(
      `/api/v1/marketplace/interviews/${interviewId}/start`,
      data
    );
  },

  async applyToInterview(interviewId: string, data: ApplyRequest): Promise<Application> {
    return apiClient.post<Application>(
      `/api/v1/marketplace/interviews/${interviewId}/apply`,
      data
    );
  },

  async listOrgApplications(orgId: string): Promise<Application[]> {
    return apiClient.get<Application[]>(`/api/v1/marketplace/org/${orgId}/applications`);
  },

  async setApplicationFit(applicationId: string, data: FitScoreRequest): Promise<Application> {
    return apiClient.post<Application>(
      `/api/v1/marketplace/applications/${applicationId}/fit`,
      data
    );
  },

  async inviteCandidate(applicationId: string): Promise<Application> {
    return apiClient.post<Application>(
      `/api/v1/marketplace/applications/${applicationId}/invite`,
      {}
    );
  },

  async respondToApplication(applicationId: string, data: CandidateResponseRequest): Promise<Application> {
    return apiClient.post<Application>(
      `/api/v1/marketplace/applications/${applicationId}/respond`,
      data
    );
  },

  async setApplicationOutcome(applicationId: string, data: ApplicationOutcomeRequest): Promise<Application> {
    return apiClient.post<Application>(
      `/api/v1/marketplace/applications/${applicationId}/outcome`,
      data
    );
  },

  // ── Org CRUD for own public listings ────────────────────────────

  async createListing(data: CreateListingRequest): Promise<OrgPublicListing> {
    return apiClient.post<OrgPublicListing>('/api/v1/marketplace/interviews', data);
  },

  async listOrgListings(orgId: string): Promise<OrgPublicListing[]> {
    return apiClient.get<OrgPublicListing[]>(`/api/v1/marketplace/org/${orgId}/interviews`);
  },

  async updateListing(interviewId: string, data: UpdateListingRequest): Promise<OrgPublicListing> {
    return apiClient.put<OrgPublicListing>(`/api/v1/marketplace/interviews/${interviewId}`, data);
  },

  async deleteListing(interviewId: string): Promise<void> {
    await apiClient.delete(`/api/v1/marketplace/interviews/${interviewId}`);
  },
};
