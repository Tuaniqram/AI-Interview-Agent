/**
 * Common utility types used across the application
 */

export type Phase = string;  // Dynamic from backend

export type InterviewView = 
  | 'start'      // Session start / company selection
  | 'question';  // Active question display

export interface InterviewFormData {
  companyId: number;
  jobRole: string;
  interviewMode: 'typing' | 'voice' | 'avatar' | 'realtime';
}

export interface ApiValidationError {
  field: string;
  message: string;
}

export interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

export interface LoadingState {
  isLoading: boolean;
  error: Error | null;
}