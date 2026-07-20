/**
 * Interview Service - Calls new LangGraph API routes
 *
 * Backend routes (from app/api/interview_agent.py):
 *   POST /interviews
 *   POST /interviews/{session_id}/questions/next
 *   POST /interviews/{session_id}/answers
 *   GET  /interviews/{session_id}/status
 *   GET  /interviews/{session_id}/summary
 *   GET  /interviews/{session_id}/rag-status
 */

import { apiClient } from './apiClient';
import {
  InterviewSession,
  Question,
  AnswerSubmitResponse,
  InterviewStatusResponse,
  InterviewReport,
} from '../types/interview';

/**
 * Backend API responses (from orchestrator):
 *
 * POST /interviews → {
 *   session_id, status, current_phase, question_number, total_questions,
 *   difficulty_level, start_time
 * }
 *
 * POST /interviews/{id}/questions/next → {
 *   session_id, question, question_number, phase, difficulty_level,
 *   next_action, suggested_follow_up, rag_context_available, nodes_executed, rag_metadata
 * }
 *
 * POST /interviews/{id}/answers → {
 *   session_id, question_number,
 *   evaluation: { score, technical_score, communication_score, strengths, weaknesses, feedback },
 *   next_phase, next_difficulty, next_action, rag_context_used, nodes_executed
 * }
 */

export class InterviewService {
  private apiClient: typeof apiClient;

  constructor(client = apiClient) {
    this.apiClient = client;
  }

  // ============================================================================
  // POST /interviews
  // Start a new interview session
  // ============================================================================
  async startSession(params: {
    company_id: number;
    job_role: string;
    candidate_id?: string;
    candidate_name?: string;
    candidate_email?: string;
    total_questions?: number;
    initial_difficulty?: number;
    interview_type?: string;
    interview_mode?: string;
  }): Promise<InterviewSession> {
    console.log('[InterviewService] startSession:', params);
    return await this.apiClient.post<InterviewSession>('/interviews', {
      company_id: params.company_id,
      job_role: params.job_role,
      candidate_id: params.candidate_id || '',
      candidate_name: params.candidate_name || '',
      candidate_email: params.candidate_email || '',
      total_questions: params.total_questions ?? 10,
      initial_difficulty: params.initial_difficulty ?? 1,
      interview_type: params.interview_type || 'company',
      interview_mode: params.interview_mode || 'avatar',
    });
  }

  // ============================================================================
  // POST /interviews/{session_id}/questions/next
  // Get AI-generated next question via LangGraph
  // ============================================================================
  async getNextQuestion(params: {
    session_id: string;
    conversation_history?: Array<{ role: string; content: string }>;
    current_phase?: string;
    question_number?: number;
    difficulty_level?: number;
    candidate_profile?: Record<string, unknown>;
  }): Promise<Question> {
    console.log('[InterviewService] getNextQuestion:', {
      session_id: params.session_id,
      qnum: params.question_number,
      phase: params.current_phase,
    });
    return await this.apiClient.post<Question>(
      `/interviews/${params.session_id}/questions/next`,
      {
        conversation_history: params.conversation_history || [],
        current_phase: params.current_phase || 'intro',
        question_number: params.question_number || 0,
        difficulty_level: params.difficulty_level || 1,
        candidate_profile: params.candidate_profile || {},
      }
    );
  }

  // ============================================================================
  // POST /interviews/{session_id}/answers
  // Submit candidate answer for LLM evaluation
  // ============================================================================
  async submitAnswer(params: {
    session_id: string;
    question_number: number;
    question: string;
    candidate_answer: string;
    conversation_history?: Array<{ role: string; content: string }>;
    candidate_profile?: Record<string, unknown>;
    difficulty_level?: number;
  }): Promise<AnswerSubmitResponse> {
    console.log('[InterviewService] submitAnswer:', {
      session_id: params.session_id,
      qnum: params.question_number,
      answer_len: params.candidate_answer.length,
    });
    return await this.apiClient.post<AnswerSubmitResponse>(
      `/interviews/${params.session_id}/answers`,
      {
        question_number: params.question_number,
        question: params.question,
        candidate_answer: params.candidate_answer,
        conversation_history: params.conversation_history || [],
        candidate_profile: params.candidate_profile || {},
        difficulty_level: params.difficulty_level || 1,
      }
    );
  }

  // ============================================================================
  // GET /interviews/{session_id}/status
  // Get current session status
  // ============================================================================
  async getSessionStatus(session_id: string): Promise<InterviewStatusResponse> {
    console.log('[InterviewService] getSessionStatus:', { session_id });
    return await this.apiClient.get<InterviewStatusResponse>(
      `/interviews/${session_id}/status`
    );
  }

  // ============================================================================
  // GET /interviews/{session_id}/summary
  // Get comprehensive session summary
  // ============================================================================
  async getSummary(session_id: string): Promise<InterviewReport> {
    console.log('[InterviewService] getSummary:', { session_id });
    return await this.apiClient.get<InterviewReport>(
      `/interviews/${session_id}/summary`
    );
  }

  // ============================================================================
  // GET /interviews/{session_id}/rag-status
  // Get RAG metadata for the session
  // ============================================================================
  async getRagStatus(session_id: string): Promise<{
    rag_available: boolean;
    rag_details: { company_id: string | number; company_requirements: boolean };
  }> {
    console.log('[InterviewService] getRagStatus:', { session_id });
    return await this.apiClient.get<{
      rag_available: boolean;
      rag_details: { company_id: string | number; company_requirements: boolean };
    }>(`/interviews/${session_id}/rag-status`);
  }
}

// Export singleton instance
export const interviewService = new InterviewService();