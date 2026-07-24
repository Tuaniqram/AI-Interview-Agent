import { apiClient } from './apiClient';
import type {
  OrgListing,
  PublicInterview,
  OrgPublicListing,
  CreateListingRequest,
  UpdateListingRequest,
  StartInterviewRequest,
  StartInterviewResponse,
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
