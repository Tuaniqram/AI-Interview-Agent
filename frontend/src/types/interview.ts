/**
 * BACKEND-DRIVEN INTERVIEW DATA CONTRACTS
 * All values come from backend API responses (app/api/interview_agent.py)
 * 
 * API endpoints:
 *   POST /interviews                          → InterviewSession
 *   POST /interviews/{session_id}/questions/next → Question
 *   POST /interviews/{session_id}/answers     → AnswerSubmitResponse
 *   GET  /interviews/{session_id}/status      → InterviewStatusResponse
 *   GET  /interviews/{session_id}/summary     → InterviewReport
 */

export type InterviewMode = 'typing' | 'voice' | 'avatar' | 'realtime';
export type InterviewStatus = 'initiating' | 'active' | 'completed' | 'initialized';

/**
 * POST /interviews Response
 * {
 *   session_id, status, current_phase, question_number, total_questions,
 *   difficulty_level, start_time
 * }
 */
export interface InterviewSession {
  session_id: string;
  status: InterviewStatus;
  current_phase: string;
  question_number: number;
  total_questions: number;
  difficulty_level?: number;
  start_time?: string;
  candidate_name?: string;
  candidate_email?: string;
  interview_mode?: InterviewMode;
}

/**
 * POST /interviews/{session_id}/questions/next Response
 * {
 *   session_id, question, question_number, phase, difficulty_level,
 *   next_action, suggested_follow_up, rag_context_available, nodes_executed, rag_metadata
 * }
 */
export interface Question {
  session_id: string;
  question: string;
  question_number: number;
  phase: string;
  difficulty_level: number;
  next_action: string;
  suggested_follow_up?: string;
  rag_context_available?: boolean;
  nodes_executed?: string[];
  rag_metadata?: Record<string, unknown>;
}

/**
 * Nested evaluation object inside POST /interviews/{session_id}/answers response
 */
export interface EvaluationDetail {
  score: number;
  technical_score?: number;
  communication_score?: number;
  strengths: string[];
  weaknesses: string[];
  feedback: string;
}

/**
 * POST /interviews/{session_id}/answers Raw Response
 * {
 *   session_id, question_number,
 *   evaluation: { score, technical_score, communication_score, strengths, weaknesses, feedback },
 *   next_phase, next_difficulty, next_action, rag_context_used, nodes_executed
 * }
 */
export interface AnswerSubmitResponse {
  session_id: string;
  question_number: number;
  evaluation: EvaluationDetail;
  next_phase: string;
  next_difficulty: number;
  next_action: string;
  rag_context_used?: boolean;
  nodes_executed?: string[];
}

export interface EvaluationHistoryEntry {
  questionNumber: number;
  question: string;
  answer: string;
  score: number;
  technicalScore?: number;
  communicationScore?: number;
  strengths: string[];
  weaknesses: string[];
  feedback: string;
}

/**
 * AnswerEvaluation - Parsed frontend-friendly version of AnswerSubmitResponse
 * This is what the controller returns to the store/UI
 */
export interface AnswerEvaluation {
  evaluation: string;  // Backend feedback text
  score: number;
  technical_score?: number;
  communication_score?: number;
  strengths: string[];
  weaknesses: string[];
  phase: string;           // Map from next_phase
  question_number: number;
  difficulty_level: number; // Map from next_difficulty
  interview_status: InterviewStatus;  // Map from next_action ("complete" → "completed")
}

/**
 * GET /interviews/{session_id}/status Response
 * {
 *   session_id, status, current_phase, question_number, total_questions,
 *   difficulty_level, elapsed_time, messages_count
 * }
 */
export interface InterviewStatusResponse {
  session_id: string;
  status: InterviewStatus;
  current_phase: string;
  question_number: number;
  total_questions: number;
  difficulty_level: number;
  elapsed_time?: string;
  messages_count?: number;
}

/**
 * GET /interviews/{session_id}/summary Response
 * {
 *   session_id, company_id, job_role, status, current_phase, question_number,
 *   total_questions, final_score, answered_ratio, total_questions_answered,
 *   messages_count, evaluations_count, interview_complete, messages, evaluations
 * }
 */
export interface InterviewReport {
  session_id: string;
  company_id?: number;
  candidate_name?: string;
  candidate_email?: string;
  job_role?: string;
  status: InterviewStatus;
  final_score: number | null;
  technical_score?: number | null;
  communication_score?: number | null;
  strengths?: string[];
  weaknesses?: string[];
  total_questions_answered: number;
  answered_ratio: number;
  total_questions: number;
  interview_complete: boolean;
  started_at?: string;
  ended_at?: string;
  messages: Array<Record<string, unknown>>;
  evaluations: Array<Record<string, unknown>>;
  messages_count: number;
  evaluations_count: number;
}