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
  ApplicationInvitation,
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
    // Multipart: apiClient.post would JSON-serialize a FormData body, so use upload().
    const form = new FormData();
    if (data.candidate_email) form.append('candidate_email', data.candidate_email);
    if (data.candidate_name) form.append('candidate_name', data.candidate_name);
    if (data.resume_document_id) form.append('resume_document_id', data.resume_document_id);
    if (data.resume) form.append('resume', data.resume);
    return apiClient.upload<Application>(
      `/api/v1/marketplace/interviews/${interviewId}/apply`,
      form
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

  /** Re-run the automatic fit evaluation (org owner). Resolves with fit_status 'pending'. */
  async evaluateApplication(applicationId: string): Promise<Application> {
    return apiClient.post<Application>(
      `/api/v1/marketplace/applications/${applicationId}/evaluate`,
      {}
    );
  },

  /** The applicant's CV as a PDF blob (fetched with auth, so it cannot be a plain link). */
  async downloadApplicationResume(applicationId: string): Promise<Blob> {
    return apiClient.request<Blob>({
      method: 'GET',
      url: `/api/v1/marketplace/applications/${applicationId}/resume`,
      responseType: 'blob',
    });
  },

  /** Public: the emailed invite token is the credential (no login needed). */
  async getApplicationInvitation(token: string): Promise<ApplicationInvitation> {
    return apiClient.get<ApplicationInvitation>(`/api/v1/marketplace/application-invitations/${token}`);
  },

  async respondToApplicationInvitation(token: string, response: 'accepted' | 'declined'): Promise<ApplicationInvitation> {
    return apiClient.post<ApplicationInvitation>(
      `/api/v1/marketplace/application-invitations/${token}/respond`,
      { response }
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
