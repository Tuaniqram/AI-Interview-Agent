import { apiClient } from './apiClient';
import type { AuthResponse, LoginRequest, MeResponse, RegisterRequest, Tokens } from '../types/auth';

export const authService = {
  async register(data: RegisterRequest): Promise<AuthResponse> {
    return apiClient.post<AuthResponse>('/api/v1/auth/register', data);
  },

  async login(data: LoginRequest): Promise<AuthResponse> {
    return apiClient.post<AuthResponse>('/api/v1/auth/login', data);
  },

  async refresh(refreshToken: string): Promise<Tokens> {
    return apiClient.post<Tokens>('/api/v1/auth/refresh', { refresh_token: refreshToken });
  },

  async logout(refreshToken: string): Promise<void> {
    await apiClient.post<void>('/api/v1/auth/logout', { refresh_token: refreshToken });
  },

  async me(): Promise<MeResponse> {
    return apiClient.get<MeResponse>('/api/v1/auth/me');
  },
};
