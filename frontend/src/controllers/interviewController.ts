import { interviewService } from '../services/interviewService';
import { interviewWebSocket } from '../services/interviewWebSocket';
import {
  InterviewSession,
  Question,
  AnswerEvaluation,
} from '../types/interview';

export class InterviewController {
  private session: InterviewSession | null = null;
  private currentQuestion: Question | null = null;
  private isEvaluating = false;
  private messageHistory: Array<{ role: string; content: string }> = [];
  private isProbing = false;

  async startInterview(params: {
    departmentId?: number;
    jobRole: string;
    totalQuestions?: number;
    mode?: string;
  }): Promise<{ session: InterviewSession; firstQuestion: Question }> {
    if (!params.jobRole.trim()) {
      throw new Error('Job role is required');
    }

    try {
      const session = await interviewService.startSession({
        department_id: params.departmentId,
        job_role: params.jobRole,
        total_questions: params.totalQuestions,
        interaction_mode: params.mode,
        session_type: params.departmentId ? 'department' : 'practice',
      });

      this.session = session;
      this.messageHistory = [];
      this.isProbing = false;

      const question = await interviewService.getNextQuestion({
        session_id: session.session_id,
        question_number: 1,
        current_phase: session.current_phase ?? 'intro',
        difficulty_level: session.difficulty_level ?? 1,
      });

      this.currentQuestion = { ...question, question_number: 1 };
      this.session.question_number = 1;

      return { session, firstQuestion: question };
    } catch (error: any) {
      console.error('Failed to start interview:', error);
      throw new Error(`Failed to start interview: ${error.message || 'Unknown error'}`);
    }
  }

  async goToNextQuestion(): Promise<Question> {
    if (!this.session || !this.currentQuestion) {
      throw new Error('No active interview session');
    }

    try {
      const history = [...this.messageHistory];

      const nextQuestion = await interviewService.getNextQuestion({
        session_id: this.session.session_id,
        conversation_history: history,
        current_phase: this.session.current_phase,
        question_number: this.currentQuestion.question_number,
        difficulty_level: this.session.difficulty_level ?? 1,
        is_follow_up: false,
      });

      const nextQNumber = (this.currentQuestion.question_number || 0) + 1;
      this.currentQuestion = { ...nextQuestion, question_number: nextQNumber };
      this.session.question_number = nextQNumber;
      this.session.current_phase = nextQuestion.phase;
      this.session.difficulty_level = nextQuestion.difficulty_level;
      this.isProbing = false;

      return nextQuestion;
    } catch (error: any) {
      console.error('Failed to fetch next question:', error);
      throw new Error(`Failed to get next question: ${error.message || 'Unknown error'}`);
    }
  }

  async submitAnswer(params: {
    answer: string;
  }): Promise<AnswerEvaluation> {
    if (!this.session || !this.currentQuestion) {
      throw new Error('No active interview session or question');
    }

    if (!params.answer.trim()) {
      throw new Error('Answer cannot be empty');
    }

    this.isEvaluating = true;

    try {
      this.messageHistory.push({
        role: 'assistant',
        content: this.currentQuestion.question,
      });

      const response = await interviewService.submitAnswer({
        session_id: this.session.session_id,
        question_number: this.currentQuestion.question_number,
        question: this.currentQuestion.question,
        candidate_answer: params.answer,
        conversation_history: this.messageHistory,
        difficulty_level: this.session.difficulty_level ?? 1,
        is_follow_up: this.isProbing,
      });

      this.messageHistory.push({
        role: 'user',
        content: params.answer,
      });

      // Handle probe flow: backend wants to dig deeper
      if (response.next_action === 'probe' && response.inquisitor_action === 'probe') {
        this.isProbing = true;

        // Fetch the probe question from backend
        const probeQuestion = await interviewService.getNextQuestion({
          session_id: this.session.session_id,
          conversation_history: this.messageHistory,
          current_phase: this.session.current_phase,
          question_number: this.currentQuestion.question_number,
          difficulty_level: this.session.difficulty_level ?? 1,
          is_follow_up: true,
        });

        this.currentQuestion = {
          ...probeQuestion,
          question_number: this.currentQuestion.question_number,
        };

        const evaluation: AnswerEvaluation = {
          evaluation: response.evaluation?.feedback || '',
          score: response.evaluation?.score ?? 0,
        phase: response.next_phase || this.session!.current_phase,
        question_number: response.question_number ?? this.currentQuestion!.question_number,
        difficulty_level: response.next_difficulty ?? this.session!.difficulty_level ?? 1,
          interview_status: 'active',
          technical_score: response.evaluation?.technical_score,
          communication_score: response.evaluation?.communication_score,
          strengths: response.evaluation?.strengths || [],
          weaknesses: response.evaluation?.weaknesses || [],
          is_follow_up: true,
          probe_angle: response.probe_angle || '',
          probing_active: true,
        };

        return evaluation;
      }

      // Normal flow (saturate / continue / finish)
      this.isProbing = false;

      const evaluation: AnswerEvaluation = {
        evaluation: response.evaluation?.feedback || '',
        score: response.evaluation?.score ?? 0,
        phase: response.next_phase || this.session.current_phase,
        question_number: response.question_number ?? this.currentQuestion.question_number,
        difficulty_level: response.next_difficulty ?? this.session.difficulty_level ?? 1,
        interview_status: response.next_action === 'finish' ? 'completed' : 'active',
        technical_score: response.evaluation?.technical_score,
        communication_score: response.evaluation?.communication_score,
        strengths: response.evaluation?.strengths || [],
        weaknesses: response.evaluation?.weaknesses || [],
        is_follow_up: false,
        probing_active: false,
      };

      this.session.current_phase = evaluation.phase;
      this.session.difficulty_level = evaluation.difficulty_level;

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

  getSession(): { session: InterviewSession | null; currentQuestion: Question | null; isEvaluating: boolean; isProbing: boolean } {
    return {
      session: this.session,
      currentQuestion: this.currentQuestion,
      isEvaluating: this.isEvaluating,
      isProbing: this.isProbing,
    };
  }

  cancelInterview(): void {
    this.session = null;
    this.currentQuestion = null;
    this.isEvaluating = false;
    this.isProbing = false;
    this.messageHistory = [];
  }

  // ── WebSocket variants ──

  async startInterviewViaWS(params: {
    departmentId?: number;
    jobRole: string;
    totalQuestions?: number;
    candidateName?: string;
    candidateEmail?: string;
    mode?: string;
  }): Promise<{ session: InterviewSession; firstQuestion: Question }> {
    const tempSessionId = 'new';
    await interviewWebSocket.connect(tempSessionId);

    const session = await interviewWebSocket.startSession({
      department_id: params.departmentId,
      job_role: params.jobRole,
      total_questions: params.totalQuestions,
      interaction_mode: params.mode,
      session_type: params.departmentId ? 'department' : 'practice',
    });

    this.session = session;
    this.messageHistory = [];
    this.isProbing = false;

    const question = await interviewWebSocket.getNextQuestion({
      session_id: session.session_id,
      question_number: 0,
      current_phase: 'intro',
      difficulty_level: 1,
    });

    this.currentQuestion = question;
    return { session, firstQuestion: question };
  }

  async goToNextQuestionViaWS(): Promise<Question> {
    if (!this.session) throw new Error('No active interview session');

    const history = [...this.messageHistory];
    const nextQuestion = await interviewWebSocket.getNextQuestion({
      session_id: this.session.session_id,
      conversation_history: history,
      current_phase: this.session.current_phase,
      question_number: this.session.question_number ?? 0,
      difficulty_level: this.session.difficulty_level ?? 1,
    });

    this.currentQuestion = nextQuestion;
    this.session.question_number = nextQuestion.question_number;
    this.session.current_phase = nextQuestion.phase;
    this.session.difficulty_level = nextQuestion.difficulty_level;
    this.isProbing = false;
    return nextQuestion;
  }

  async submitAnswerViaWS(params: { answer: string }): Promise<AnswerEvaluation> {
    if (!this.session || !this.currentQuestion) throw new Error('No active session');

    this.isEvaluating = true;
    try {
      this.messageHistory.push({ role: 'assistant', content: this.currentQuestion.question });

      const response = await interviewWebSocket.submitAnswer({
        session_id: this.session.session_id,
        question_number: this.currentQuestion.question_number,
        question: this.currentQuestion.question,
        candidate_answer: params.answer,
        conversation_history: this.messageHistory,
        difficulty_level: this.session.difficulty_level ?? 1,
      });

      this.messageHistory.push({ role: 'user', content: params.answer });

      const isProbeResponse = response.next_action === 'probe';

      if (isProbeResponse) {
        this.isProbing = true;
        const probeQuestion = await interviewWebSocket.getNextQuestion({
          session_id: this.session.session_id,
          conversation_history: this.messageHistory,
          current_phase: this.session.current_phase,
          question_number: this.currentQuestion.question_number,
          difficulty_level: this.session.difficulty_level ?? 1,
        });
        this.currentQuestion = {
          ...probeQuestion,
          question_number: this.currentQuestion.question_number,
        };
      } else {
        this.isProbing = false;
      }

      const evaluation: AnswerEvaluation = {
        evaluation: response.evaluation?.feedback || '',
        score: response.evaluation?.score ?? 0,
        phase: response.next_phase || this.session.current_phase,
        question_number: response.question_number ?? this.currentQuestion!.question_number,
        difficulty_level: response.next_difficulty ?? this.session.difficulty_level ?? 1,
        interview_status: response.next_action === 'finish' ? 'completed' : 'active',
        technical_score: response.evaluation?.technical_score,
        communication_score: response.evaluation?.communication_score,
        strengths: response.evaluation?.strengths || [],
        weaknesses: response.evaluation?.weaknesses || [],
        is_follow_up: isProbeResponse,
        probing_active: isProbeResponse,
      };

      if (!isProbeResponse && this.session) {
        this.session.current_phase = evaluation.phase;
        this.session.question_number = evaluation.question_number;
        this.session.difficulty_level = evaluation.difficulty_level;
        if (evaluation.interview_status === 'completed') {
          this.session.status = 'completed';
        }
      }

      return evaluation;
    } finally {
      this.isEvaluating = false;
    }
  }

  cancelInterviewWS(): void {
    interviewWebSocket.disconnect();
    this.cancelInterview();
  }
}

export const interviewController = new InterviewController();
