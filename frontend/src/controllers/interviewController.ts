/**
 * Interview Controller - Business Logic Layer
 * 
 * Responsibilities:
 * - Orchestrate service calls
 * - Handle state transitions
 * - Coordinate interview flow
 * - NO hardcoded logic (all flows come from backend responses)
 * 
 * Architecture:
 * UI Component (interview.tsx)
 *     ↓
 * InterviewStore (actions)
 *     ↓
 * InterviewController (Business Logic) ← This file
 *     ↓
 * InterviewService (API Calls)
 *     ↓
 * API Client (HTTP)
 */

import { interviewService } from '../services/interviewService';
import { 
  InterviewSession, 
  Question, 
  AnswerEvaluation,
} from '../types/interview';

/**
 * Interview Controller - Tier 3: Business Logic Layer
 * 
 * KEY PRINCIPLE:
 * - All interview flow is CONTROLLED by backend responses
 * - NO hardcoded phase transitions
 * - NO hardcoded question counts
 * - NO hardcoded difficulty ranges
 * - Frontend ONLY displays and sends data
 * 
 * API Contract (from app/api/interview_agent.py):
 *   POST /interviews                          → session info
 *   POST /interviews/{id}/questions/next     → question
 *   POST /interviews/{id}/answers            → evaluation
 *   GET  /interviews/{id}/status             → status
 *   GET  /interviews/{id}/summary            → full report
 */

export class InterviewController {
  private session: InterviewSession | null = null;
  private currentQuestion: Question | null = null;
  private isEvaluating = false;
  private messageHistory: Array<{ role: string; content: string }> = [];

  /**
   * Initialize and start a new interview session
   * 
   * Flow:
   * 1. Controller calls startSession()
   * 2. Backend returns session with totalQuestions, phase, etc.
   * 3. Controller saves session state
   * 4. Controller calls getNextQuestion() for first question
   */
  async startInterview(params: {
    companyId: number;
    jobRole: string;
    totalQuestions?: number;
    candidateName?: string;
    candidateEmail?: string;
    mode?: string;
  }): Promise<{ session: InterviewSession; firstQuestion: Question }> {
    if (!params.jobRole.trim()) {
      throw new Error('Job role is required');
    }

    try {
      const session = await interviewService.startSession({
        company_id: params.companyId,
        job_role: params.jobRole,
        total_questions: params.totalQuestions,
        candidate_name: params.candidateName,
        candidate_email: params.candidateEmail,
        interview_mode: params.mode,
      });

      console.log('[Controller] startInterview session:', session);

      // Store session state
      this.session = session;
      this.messageHistory = [];

      // Backend auto-generates first question
      const question = await interviewService.getNextQuestion({
        session_id: session.session_id,
        question_number: session.question_number ?? 0,
        current_phase: session.current_phase ?? 'intro',
        difficulty_level: session.difficulty_level ?? 1,
      });

      console.log('[Controller] startInterview firstQuestion:', question);

      // Store current question
      this.currentQuestion = question;

      return { session, firstQuestion: question };
    } catch (error: any) {
      console.error('Failed to start interview:', error);
      throw new Error(`Failed to start interview: ${error.message || 'Unknown error'}`);
    }
  }

  /**
   * Get next question
   * 
   * IMPORTANT: The backend decides everything:
   * - Next question number
   * - Phase transitions
   * - Difficulty adaptation
   * - Conversation context
   */
  async goToNextQuestion(): Promise<Question> {
    if (!this.session || !this.currentQuestion) {
      throw new Error('No active interview session');
    }

    try {
      console.log('[Controller] goToNextQuestion:', {
        session_id: this.session.session_id,
        question_number: this.session.question_number,
        phase: this.session.current_phase,
      });

      // Build conversation history from stored messages
      const history = [...this.messageHistory];

      // Get next question from backend
      const nextQuestion = await interviewService.getNextQuestion({
        session_id: this.session.session_id,
        conversation_history: history,
        current_phase: this.session.current_phase,
        question_number: this.session.question_number ?? 0,
        difficulty_level: this.session.difficulty_level ?? 1,
      });

      console.log('[Controller] goToNextQuestion response:', nextQuestion);

      // Update state from backend response
      this.currentQuestion = nextQuestion;
      this.session.question_number = nextQuestion.question_number;
      this.session.current_phase = nextQuestion.phase;
      this.session.difficulty_level = nextQuestion.difficulty_level;

      return nextQuestion;
    } catch (error: any) {
      console.error('Failed to fetch next question:', error);
      throw new Error(`Failed to get next question: ${error.message || 'Unknown error'}`);
    }
  }

  /**
   * Submit answer for evaluation
   * 
   * Backend controls:
   * - Scoring (LLM-based)
   * - Difficulty adjustment
   * - Phase transition
   * - Next action decision
   * 
   * Frontend only sends: question, answer, and session context
   */
  async submitAnswer(params: {
    answer: string;
  }): Promise<AnswerEvaluation> {
    if (!this.session || !this.currentQuestion) {
      throw new Error('No active interview session or question');
    }

    if (!params.answer.trim()) {
      throw new Error('Answer cannot be empty');
    }

    // Set evaluating state
    this.isEvaluating = true;

    try {
      console.log('[Controller] submitAnswer:', {
        session_id: this.session.session_id,
        question: this.currentQuestion.question.substring(0, 80),
        answer_length: params.answer.length,
        number: this.currentQuestion.question_number,
      });

      // Add current Q&A to conversation history before sending
      this.messageHistory.push({
        role: 'assistant',
        content: this.currentQuestion.question,
      });

      // Submit answer via service - matches new API
      const response = await interviewService.submitAnswer({
        session_id: this.session.session_id,
        question_number: this.currentQuestion.question_number,
        question: this.currentQuestion.question,
        candidate_answer: params.answer,
        conversation_history: this.messageHistory,
        difficulty_level: this.session.difficulty_level ?? 1,
      });

      console.log('[Controller] submitAnswer response:', response);

      // Add answer to history
      this.messageHistory.push({
        role: 'user',
        content: params.answer,
      });

      // The response structure from the new API has:
      // { session_id, question_number, evaluation: { score, technical_score, ... },
      //   next_phase, next_difficulty, next_action }
      // We need to map it to the frontend's AnswerEvaluation type
      const evaluation: AnswerEvaluation = {
        evaluation: response.evaluation?.feedback || '',
        score: response.evaluation?.score ?? 0,
        phase: response.next_phase || this.session.current_phase,
        question_number: response.question_number ?? this.currentQuestion.question_number,
        difficulty_level: response.next_difficulty ?? this.session.difficulty_level ?? 1,
        interview_status: response.next_action === 'complete' ? 'completed' : 'active',
        technical_score: response.evaluation?.technical_score,
        communication_score: response.evaluation?.communication_score,
        strengths: response.evaluation?.strengths || [],
        weaknesses: response.evaluation?.weaknesses || [],
      };

      // Update session with backend's decisions
      this.session.current_phase = evaluation.phase;
      this.session.question_number = evaluation.question_number;
      this.session.difficulty_level = evaluation.difficulty_level;

      // If completed, update status
      if (evaluation.interview_status === 'completed') {
        this.session.status = 'completed';
      }

      return evaluation;
    } catch (error: any) {
      console.error('Failed to submit answer:', error);
      throw new Error(`Failed to submit answer: ${error.message || 'Unknown error'}`);
    } finally {
      this.isEvaluating = false;
    }
  }

  /**
   * Get current session info
   */
  getSession(): { session: InterviewSession | null; currentQuestion: Question | null; isEvaluating: boolean } {
    return {
      session: this.session,
      currentQuestion: this.currentQuestion,
      isEvaluating: this.isEvaluating,
    };
  }

  /**
   * Abandon interview (client-side only, no server cancel endpoint)
   */
  cancelInterview(): void {
    this.session = null;
    this.currentQuestion = null;
    this.isEvaluating = false;
    this.messageHistory = [];
  }
}

// Export singleton instance
export const interviewController = new InterviewController();