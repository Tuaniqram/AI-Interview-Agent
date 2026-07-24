import { apiClient } from './apiClient';

export interface Department {
  id: number;
  org_id?: string;
  name: string;
  website?: string | null;
  description?: string | null;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  document_type: string;
  pinecone_namespace: string;
  created_at: string;
}

export interface Template {
  id: string;
  department_id: number;
  name: string;
  job_role: string;
  total_questions: number;
}

export interface SessionRecord {
  id: string;
  job_role: string;
  status: string;
  final_score: number | null;
  started_at: string;
  interaction_mode?: string;
  department_name?: string;
}

export const departmentService = {
  async listDepartments(): Promise<Department[]> {
    return apiClient.get<Department[]>('/api/v1/departments');
  },

  async getDepartment(departmentId: number): Promise<Department> {
    return apiClient.get<Department>(`/api/v1/departments/${departmentId}`);
  },

  async createDepartment(data: { name: string; website?: string; description?: string }): Promise<Department> {
    return apiClient.post<Department>('/api/v1/departments', data);
  },

  async updateDepartment(departmentId: number, data: { name?: string; website?: string; description?: string }): Promise<Department> {
    return apiClient.patch<Department>(`/api/v1/departments/${departmentId}`, data);
  },

  async deleteDepartment(departmentId: number): Promise<void> {
    await apiClient.delete(`/api/v1/departments/${departmentId}`);
  },

  async listDocuments(departmentId: number): Promise<Document[]> {
    return apiClient.get<Document[]>(`/api/v1/departments/${departmentId}/documents`);
  },

  async uploadDocument(departmentId: number, file: File): Promise<{ message: string; doc_id: string; filename: string; status: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`/api/v1/departments/${departmentId}/documents`, formData);
  },

  async deleteDocument(departmentId: number, docId: string): Promise<void> {
    await apiClient.delete(`/api/v1/departments/${departmentId}/documents/${docId}`);
  },

  async listSessions(departmentId: number): Promise<SessionRecord[]> {
    return apiClient.get<SessionRecord[]>(`/api/v1/departments/${departmentId}/sessions`);
  },

  async listTemplates(departmentId: number): Promise<Template[]> {
    return apiClient.get<Template[]>(`/api/v1/departments/${departmentId}/templates`);
  },

  async createTemplate(departmentId: number, data: { name: string; job_role: string; total_questions?: number }): Promise<Template> {
    return apiClient.post<Template>(`/api/v1/departments/${departmentId}/templates`, data);
  },
};
