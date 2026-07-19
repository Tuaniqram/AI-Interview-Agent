/**
 * API Client - Centralized HTTP wrapper with error handling and interceptors
 * UI components should NEVER call fetch/axios directly
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import { ErrorResponse, ApiConfig } from '../types/api';

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

    // Request interceptor for logging and token management
    this.instance.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data);
        return config;
      },
      (error) => {
        console.error('Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling and token refresh
    this.instance.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.config.url}`, response);
        return response;
      },
      async (error: AxiosError<ErrorResponse>) => {
        console.error('API Error:', error.response?.status, error.response?.data);
        
        // Handle specific error scenarios
        await this.handleErrorResponse(error);
        
        return Promise.reject(error);
      }
    );
  }

  /**
   * Centralized error handling for different scenarios
   */
  private async handleErrorResponse(error: AxiosError<ErrorResponse>): Promise<void> {
    const status = error.response?.status;

    switch (status) {
      case 401:
        // Session expired/invalid - redirect to start or logout
        console.error('Unauthorized - Session expired');
        // TODO: Implement session refresh or redirect
        break;
      case 403:
        // Permission denied
        console.error('Forbidden - Insufficient permissions');
        break;
      case 404:
        // Not found
        console.error('Not found - Resource not available');
        break;
      case 422:
        // Validation error
        console.error('Validation error:', error.response?.data);
        break;
      case 429:
        // Rate limit
        console.error('Too many requests - Rate limited');
        break;
      case 500:
      case 502:
      case 503:
      case 504:
        // Server errors with retry logic
        console.error('Server error - Attempting retry');
        await this.retryRequest(error.config);
        break;
      default:
        // Unknown errors
        console.error('Unknown API error');
    }
  }

  /**
   * Retry logic for transient network failures
   */
  private async retryRequest(config: AxiosRequestConfig | undefined, attempts = 1): Promise<void> {
    if (!config || attempts >= 3) return;

    const delay = Math.pow(2, attempts) * 1000; // Exponential backoff

    console.log(`Retry ${attempts} in ${delay}ms...`);
    await new Promise(resolve => setTimeout(resolve, delay));

    try {
      await this.instance.request(config);
    } catch (retryError) {
      console.error(`Retry ${attempts} failed`);
      await this.retryRequest(config, attempts + 1);
    }
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

  /**
   * Get current config
   */
  getConfig(): ApiConfig {
    return { ...this.config };
  }
}

// Export singleton instance
export const apiClient = new ApiClient();