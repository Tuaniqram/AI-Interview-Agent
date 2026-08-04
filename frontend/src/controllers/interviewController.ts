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
    scorecardTemplateId?: string;
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
        scorecard_template_id: params.scorecardTemplateId,
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

  // ── WebSocket variants (v4 / AURA engine) ──

  private mapStartQuestion(data: any): { session: InterviewSession; firstQuestion: Question; conversationTurn: string } {
    const q = data?.question || {};
    const session: InterviewSession = {
      session_id: data.session_id,
      status: 'active',
      current_phase: 'intro',
      question_number: q.number ?? 1,
      total_questions: 10,
      difficulty_level: data.difficulty ?? 1,
      interaction_mode: 'typing',
      job_role: data.job_role,
      department_id: data.department_id ?? null,
    };
    const question: Question = {
      session_id: data.session_id,
      question: q.text || '',
      question_number: q.number ?? 1,
      phase: q.target_competency || 'intro',
      difficulty_level: data.difficulty ?? 1,
      next_action: 'continue',
    };
    this.session = session;
    this.currentQuestion = question;
    this.isProbing = false;
    return { session, firstQuestion: question, conversationTurn: data.conversation_turn || '' };
  }

  async initInterviewViaWS(sessionId: string): Promise<{ session: InterviewSession; firstQuestion: Question; conversationTurn: string; resumed: boolean }> {
    await interviewWebSocket.connect(sessionId);

    // Resume if the engine already has state for this session
    try {
      const snapshot = await interviewWebSocket.getStatus(sessionId);
      if (snapshot?.current_question) {
        const mapped = this.mapStartQuestion({
          session_id: sessionId,
          status: 'in_progress',
          job_role: snapshot.job_role,
          department_id: snapshot.department_id,
          difficulty: snapshot.difficulty,
          question: { text: snapshot.current_question, number: snapshot.question_number, target_competency: '' },
          conversation_turn: snapshot.conversation_turn,
        });
        return { ...mapped, resumed: true };
      }
    } catch {
      // Engine has no state — fresh start below
    }

    const data = await interviewWebSocket.startSession({ session_id: sessionId });
    const mapped = this.mapStartQuestion(data);
    return { ...mapped, resumed: false };
  }

  async goToNextQuestionViaWS(): Promise<Question> {
    if (!this.session) throw new Error('No active interview session');
    const data = await interviewWebSocket.getNextQuestion({ session_id: this.session.session_id });
    this.currentQuestion = {
      session_id: this.session.session_id,
      question: data?.question?.text || '',
      question_number: data?.question?.number ?? this.session.question_number,
      phase: data?.question?.target_competency || 'intro',
      difficulty_level: data?.difficulty ?? 1,
      next_action: 'continue',
    };
    return this.currentQuestion;
  }

  async submitAnswerViaWS(params: { answer: string }): Promise<AnswerEvaluation> {
    if (!this.session || !this.currentQuestion) throw new Error('No active session');

    this.isEvaluating = true;
    try {
      const response = await interviewWebSocket.submitAnswer({
        session_id: this.session.session_id,
        question_number: this.currentQuestion.question_number,
        question: this.currentQuestion.question,
        candidate_answer: params.answer,
      });

      this.messageHistory.push({ role: 'assistant', content: this.currentQuestion.question });
      this.messageHistory.push({ role: 'user', content: params.answer });

      // ── Completed: report response ──
      if (response.type === 'report' || response.status === 'completed') {
        this.isProbing = false;
        this.session.status = 'completed';
        const evaluation: AnswerEvaluation = {
          evaluation: response.hiring_recommendation?.verdict || 'Interview complete',
          score: response.hiring_recommendation?.composite_score ?? 0,
          phase: this.session.current_phase,
          question_number: this.currentQuestion.question_number,
          difficulty_level: this.session.difficulty_level ?? 1,
          interview_status: 'completed',
          strengths: [],
          weaknesses: [],
          conversationTurn: response.conversation_turn || '',
        };
        return evaluation;
      }

      // ── In progress: evaluation + next question ──
      const scores = response?.evaluation?.scores || {};
      const scoredDims = Object.entries(scores)
        .filter(([, v]: [string, any]) => v?.score != null)
        .map(([dim, v]: [string, any]) => ({ dim, ...v }));

      const composite = response?.evaluation?.composite;
      const score = typeof composite === 'number'
        ? composite
        : scoredDims.length
          ? scoredDims.reduce((s, d) => s + (d.score ?? 0), 0) / scoredDims.length
          : 0;

      const strengths = scoredDims.flatMap((d) => d.strengths || []);
      const weaknesses = scoredDims.flatMap((d) => d.weaknesses || []);
      const feedback = scoredDims
        .map((d) => `${d.dim}: ${(d.score ?? 0).toFixed(1)}/10`)
        .join(' · ') || (response.hiring_recommendation?.verdict || '');

      const nextQ = response?.next_question || {};
      if (nextQ.text) {
        this.currentQuestion = {
          session_id: this.session.session_id,
          question: nextQ.text,
          question_number: nextQ.number ?? (this.currentQuestion.question_number || 0) + 1,
          phase: nextQ.target_competency || this.currentQuestion.phase,
          difficulty_level: this.session.difficulty_level ?? 1,
          next_action: 'continue',
        };
        this.session.question_number = this.currentQuestion.question_number;
      }
      this.isProbing = false;

      return {
        evaluation: feedback,
        score,
        phase: this.session.current_phase,
        question_number: this.currentQuestion.question_number,
        difficulty_level: this.session.difficulty_level ?? 1,
        interview_status: 'active',
        strengths,
        weaknesses,
        conversationTurn: response.conversation_turn || '',
      };
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
