import { apiClient } from './apiClient';

export const invitationService = {
  async verify(token: string): Promise<{
    valid: boolean;
    candidate_name: string;
    candidate_email: string;
    job_role: string;
    department_name: string | null;
  }> {
    return apiClient.get(`/api/v1/invitations/${token}`);
  },

  async accept(token: string): Promise<{
    session_id: string;
    candidate_id: string;
    candidate_name: string;
    candidate_email: string;
    job_role: string;
  }> {
    return apiClient.post(`/api/v1/invitations/${token}/accept`);
  },
};
