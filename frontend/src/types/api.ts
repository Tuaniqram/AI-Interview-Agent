export interface ErrorResponse {
  detail: string;
  status_code: number;
}

export interface ApiConfig {
  baseURL: string;
  timeout?: number;
}

export interface RequestConfig {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  data?: any;
  params?: any;
}