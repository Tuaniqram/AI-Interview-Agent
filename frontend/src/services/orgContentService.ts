import { apiClient } from './apiClient';

export interface Document {
  id: string;
  filename: string;
  document_type: string;
  pinecone_namespace: string;
  created_at: string;
}

export interface Template {
  id: string;
  name: string;
  job_role: string;
  total_questions: number;
  description?: string | null;
  interview_style?: string | null;
  competencies?: any[] | null;
  scorecard_template_id?: string | null;
  created_at?: string | null;
}

export interface SessionRecord {
  id: string;
  job_role: string;
  status: string;
  final_score: number | null;
  started_at: string;
  interaction_mode?: string;
}

export const orgContentService = {
  async listDocuments(orgId: string): Promise<Document[]> {
    return apiClient.get<Document[]>(`/api/v1/orgs/${orgId}/documents`);
  },

  async uploadDocument(orgId: string, file: File): Promise<{ message: string; doc_id: string; filename: string; status: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.upload(`/api/v1/orgs/${orgId}/documents`, formData);
  },

  async deleteDocument(orgId: string, docId: string): Promise<void> {
    await apiClient.delete(`/api/v1/orgs/${orgId}/documents/${docId}`);
  },

  async listSessions(orgId: string): Promise<SessionRecord[]> {
    return apiClient.get<SessionRecord[]>(`/api/v1/orgs/${orgId}/sessions`);
  },

  async listTemplates(orgId: string): Promise<Template[]> {
    return apiClient.get<Template[]>(`/api/v1/orgs/${orgId}/templates`);
  },

  async createTemplate(orgId: string, data: { name: string; job_role: string; total_questions?: number; description?: string; interview_style?: string; scorecard_template_id?: string; competencies?: any[] }): Promise<Template> {
    return apiClient.post<Template>(`/api/v1/orgs/${orgId}/templates`, data);
  },

  async getTemplate(orgId: string, templateId: string): Promise<Template> {
    return apiClient.get<Template>(`/api/v1/orgs/${orgId}/templates/${templateId}`);
  },

  async updateTemplate(orgId: string, templateId: string, data: Partial<Template>): Promise<Template> {
    return apiClient.put<Template>(`/api/v1/orgs/${orgId}/templates/${templateId}`, data);
  },

  async deleteTemplate(orgId: string, templateId: string): Promise<void> {
    await apiClient.delete(`/api/v1/orgs/${orgId}/templates/${templateId}`);
  },
};
