/**
 * API Client - Centralized HTTP wrapper with error handling and interceptors
 * UI components should NEVER call fetch/axios directly
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import { ErrorResponse, ApiConfig } from '../types/api';
import { getCandidateToken } from '../utils/candidateToken';

class ApiClient {
  private instance: AxiosInstance;
  private config: ApiConfig;

  constructor(config: ApiConfig = { baseURL: 'http://localhost:8000' }) {
    this.config = config;

    this.instance = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || Number(import.meta.env.VITE_API_TIMEOUT) || 120000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.instance.interceptors.request.use(
      (config) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        const orgId = this.getActiveOrgId();
        if (orgId) {
          config.headers['X-Org-Id'] = orgId;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.instance.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<ErrorResponse>) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          try {
            const newToken = await this.refreshToken();
            if (newToken && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return this.instance.request(originalRequest);
            }
          } catch {
            this.onAuthFailure?.();
            this.onCandidateAuthFailure?.();
          }
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * Generic request method with all features
   */
  async request<T>(config: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.instance.request(config);
      return response.data as T;
    } catch (error) {
      throw error;
    }
  }

  /**
   * GET request
   */
  async get<T>(url: string, params?: any): Promise<T> {
    const config: AxiosRequestConfig = {
      method: 'GET',
      url,
      params,
    };
    return await this.request<T>(config);
  }

  /**
   * POST request
   */
  async post<T>(url: string, data?: any): Promise<T> {
    const config: AxiosRequestConfig = {
      method: 'POST',
      url,
      data,
    };
    return await this.request<T>(config);
  }

  /**
   * PUT request
   */
  async put<T>(url: string, data?: any): Promise<T> {
    const config: AxiosRequestConfig = {
      method: 'PUT',
      url,
      data,
    };
    return await this.request<T>(config);
  }

  /**
   * DELETE request
   */
  async delete<T>(url: string, params?: any): Promise<T> {
    const config: AxiosRequestConfig = {
      method: 'DELETE',
      url,
      params,
    };
    return await this.request<T>(config);
  }

  /**
   * Set base URL (useful for environment switching)
   */
  setBaseURL(url: string): void {
    this.config.baseURL = url;
    this.instance.defaults.baseURL = url;
  }

  async patch<T>(url: string, data?: any): Promise<T> {
    const config: AxiosRequestConfig = {
      method: 'PATCH',
      url,
      data,
    };
    return await this.request<T>(config);
  }

  getConfig(): ApiConfig {
    return { ...this.config };
  }

  private tokenSource: 'candidate' | 'org' | null = null;

  private getAccessToken(): string | null {
    const candidate = getCandidateToken();
    if (candidate) {
      this.tokenSource = 'candidate';
      return candidate;
    }
    const org = this._getOrgUserToken();
    if (org) {
      this.tokenSource = 'org';
      return org;
    }
    this.tokenSource = null;
    return null;
  }

  private _getOrgUserToken(): string | null {
    try {
      const stored = localStorage.getItem('auth_tokens');
      if (stored) {
        const tokens = JSON.parse(stored);
        return tokens.access_token || null;
      }
    } catch { /* ignore */ }
    return null;
  }

  private getActiveOrgId(): string | null {
    if (this.tokenSource === 'candidate') return null;
    try {
      return localStorage.getItem('active_org_id');
    } catch { /* ignore */ }
    return null;
  }

  private async refreshToken(): Promise<string | null> {
    if (this.tokenSource === 'candidate') {
      return this._refreshCandidateToken();
    }
    return this._refreshOrgUserToken();
  }

  private async _refreshCandidateToken(): Promise<string | null> {
    try {
      const stored = localStorage.getItem('candidate_tokens');
      if (!stored) return null;
      const tokens = JSON.parse(stored);
      const res = await axios.post(`${this.config.baseURL}/api/v1/candidates/refresh`, {
        refresh_token: tokens.refresh_token,
      });
      const newTokens = res.data;
      localStorage.setItem('candidate_tokens', JSON.stringify(newTokens));
      return newTokens.access_token;
    } catch {
      return null;
    }
  }

  private async _refreshOrgUserToken(): Promise<string | null> {
    try {
      const stored = localStorage.getItem('auth_tokens');
      if (!stored) return null;
      const tokens = JSON.parse(stored);
      const res = await axios.post(`${this.config.baseURL}/api/v1/auth/refresh`, {
        refresh_token: tokens.refresh_token,
      });
      const newTokens = res.data;
      localStorage.setItem('auth_tokens', JSON.stringify(newTokens));
      return newTokens.access_token;
    } catch {
      return null;
    }
  }

  onAuthFailure: (() => void) | null = null;
  onCandidateAuthFailure: (() => void) | null = null;
}

export const apiClient = new ApiClient();