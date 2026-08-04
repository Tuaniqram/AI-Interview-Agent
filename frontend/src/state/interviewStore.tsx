/**
 * Interview Store - React Context for global interview state
 * Centralized state management with context API
 */

import React, { createContext, useContext, useReducer, useMemo, useRef, useEffect, useCallback, ReactNode } from 'react';
import { 
  InterviewSession, 
  Question, 
  AnswerEvaluation, 
  EvaluationHistoryEntry,
  InterviewReport,
  InterviewMode,
  InterviewStatus
} from '../types/interview';
import { interviewController } from '../controllers/interviewController';
import { interviewWebSocket } from '../services/interviewWebSocket';

// ========== STATE TYPES ==========

export type InterviewState = {
  // Session info (from backend)
  session: InterviewSession | null;
  
  // Current question (from backend)
  currentQuestion: Question | null;
  
  // User answer (controlled by UI)
  userAnswer: string;
  
  // Evaluation results (from backend)
  evaluation: AnswerEvaluation | null;
  evaluationHistory: EvaluationHistoryEntry[];
  historyIndex: number;
  cardVisible: boolean;
  finalReport: InterviewReport | null;

  // AURA conductor turn (spoken message for the current/pending question)
  conversationTurn: string;

  // AURA engine phase pushed over WebSocket (drives AuraCore states)
  wsPhase: 'idle' | 'evaluating' | 'question_ready' | 'reconnecting';

  // Interview mode
  interviewMode: InterviewMode;
  
  // Loading states
  isLoading: boolean;
  isEvaluating: boolean;
  
  // Error state
  error: string | null;
  
  // API configuration
  companyList: Array<{ id: number; name: string }>;
  currentCompanyId: number | null;
  apiURL: string;
};

type InterviewAction =
  | { type: 'SET_SESSION'; payload: InterviewSession }
  | { type: 'SET_SESSION_PHASE'; payload: string }
  | { type: 'SET_QUESTION'; payload: Question }
  | { type: 'SET_USER_ANSWER'; payload: string }
  | { type: 'SET_EVALUATION'; payload: AnswerEvaluation }
  | { type: 'PUSH_EVALUATION'; payload: EvaluationHistoryEntry }
  | { type: 'SET_HISTORY_INDEX'; payload: number }
  | { type: 'TOGGLE_CARD' }
  | { type: 'SET_FINAL_REPORT'; payload: InterviewReport }
  | { type: 'SET_CONVERSATION_TURN'; payload: string }
  | { type: 'SET_WS_PHASE'; payload: 'idle' | 'evaluating' | 'question_ready' | 'reconnecting' }
  | { type: 'SET_INTERVIEW_MODE'; payload: InterviewMode }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_EVALUATING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'SET_COMPANY_LIST'; payload: Array<{ id: number; name: string }> }
  | { type: 'SET_CURRENT_COMPANY'; payload: number }
  | { type: 'SET_API_URL'; payload: string }
  | { type: 'RESET_STATE' };

const initialState: InterviewState = {
  session: null,
  currentQuestion: null,
  userAnswer: '',
  evaluation: null,
  evaluationHistory: [],
  historyIndex: -1,
  cardVisible: false,
  finalReport: null,
  conversationTurn: '',
  wsPhase: 'idle',
  interviewMode: (localStorage.getItem('aiInterviewMode') as InterviewMode) || 'avatar',
  isLoading: false,
  isEvaluating: false,
  error: null,
  companyList: [],
  currentCompanyId: null,
  apiURL: 'http://localhost:8000',
};

// ========== REDUCER ==========

function interviewReducer(state: InterviewState, action: InterviewAction): InterviewState {
  switch (action.type) {
    case 'SET_SESSION':
      if (action.payload.interaction_mode) {
        localStorage.setItem('aiInterviewMode', action.payload.interaction_mode);
      }
      return {
        ...state,
        session: action.payload,
        isLoading: false,
      };

    case 'SET_SESSION_PHASE':
      return {
        ...state,
        session: state.session ? { ...state.session, current_phase: action.payload } : state.session,
      };

    case 'SET_QUESTION':
      return {
        ...state,
        currentQuestion: action.payload,
        isLoading: false,
      };

    case 'SET_USER_ANSWER':
      return {
        ...state,
        userAnswer: action.payload,
      };

    case 'SET_EVALUATION':
      return {
        ...state,
        evaluation: action.payload,
        isEvaluating: false,
      };

    case 'PUSH_EVALUATION':
      return {
        ...state,
        evaluationHistory: [...state.evaluationHistory, action.payload],
        historyIndex: state.evaluationHistory.length,
      };

    case 'SET_HISTORY_INDEX':
      return {
        ...state,
        historyIndex: action.payload,
      };

    case 'TOGGLE_CARD':
      return {
        ...state,
        cardVisible: !state.cardVisible,
      };

    case 'SET_FINAL_REPORT':
      return {
        ...state,
        finalReport: action.payload,
      };

    case 'SET_CONVERSATION_TURN':
      return {
        ...state,
        conversationTurn: action.payload,
      };

    case 'SET_WS_PHASE':
      return {
        ...state,
        wsPhase: action.payload,
      };

    case 'SET_INTERVIEW_MODE':
      localStorage.setItem('aiInterviewMode', action.payload);
      return {
        ...state,
        interviewMode: action.payload,
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
        error: null,
      };

    case 'SET_EVALUATING':
      return {
        ...state,
        isEvaluating: action.payload,
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        isLoading: false,
        isEvaluating: false,
      };

    case 'SET_COMPANY_LIST':
      return {
        ...state,
        companyList: action.payload,
      };

    case 'SET_CURRENT_COMPANY':
      return {
        ...state,
        currentCompanyId: action.payload,
      };

    case 'SET_API_URL':
      return {
        ...state,
        apiURL: action.payload,
      };

    case 'RESET_STATE':
      sessionStorage.removeItem('aiInterviewState');
      return initialState;

    default:
      return state;
  }
}

// ========== CONTEXT ==========

interface InterviewContextType {
  state: InterviewState;
  dispatch: React.Dispatch<InterviewAction>;
  actions: InterviewStoreActions;
}

const InterviewContext = createContext<InterviewContextType | undefined>(undefined);

// ========== ACTIONS ==========

interface InterviewStoreActions {
  startInterview: (params: { sessionId: string }) => Promise<void>;
  cancelInterview: () => void;
  fetchFinalReport: () => Promise<void>;
  goToNextQuestion: () => Promise<void>;
  submitAnswer: (answer: string) => Promise<void>;
  updateAnswer: (answer: string) => void;
  goToPrevEvaluation: () => void;
  goToNextEvaluation: () => void;
  toggleCard: () => void;
  clearError: () => void;
}

// ========== PROVIDER ==========

interface InterviewProviderProps {
  children: ReactNode;
}

function initState(defaultState: InterviewState): InterviewState {
  try {
    const saved = sessionStorage.getItem('aiInterviewState');
    if (saved) {
      const parsed = JSON.parse(saved);
      return { ...defaultState, ...parsed, isLoading: false, isEvaluating: false, error: null };
    }
  } catch {}
  return defaultState;
}

export function InterviewProvider({ children }: InterviewProviderProps) {
  const [state, dispatch] = useReducer(interviewReducer, initialState, initState);
  const controller = interviewController;
  const wsOffRef = useRef<(() => void) | null>(null);
  const closeOffRef = useRef<(() => void) | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stateRef = useRef(state);
  stateRef.current = state;

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    const sessionId = sessionIdRef.current;
    if (!sessionId) return;
    if (reconnectTimerRef.current) return;

    const attempts = reconnectAttemptsRef.current + 1;
    reconnectAttemptsRef.current = attempts;
    if (attempts > 5) {
      dispatch({ type: 'SET_ERROR', payload: 'Connection lost. Reload the page to continue the interview.' });
      return;
    }

    const delay = Math.min(1000 * 2 ** (attempts - 1), 20000);
    reconnectTimerRef.current = setTimeout(async () => {
      reconnectTimerRef.current = null;
      dispatch({ type: 'SET_WS_PHASE', payload: 'reconnecting' });
      try {
        // Reconnect + reconcile: get_status resumes when the engine still has
        // state, otherwise a fresh start is issued (both idempotent).
        const result = await controller.initInterviewViaWS(sessionId);
        reconnectAttemptsRef.current = 0;
        dispatch({ type: 'SET_ERROR', payload: '' });
        dispatch({ type: 'SET_SESSION', payload: result.session });
        dispatch({ type: 'SET_QUESTION', payload: result.firstQuestion });
        dispatch({ type: 'SET_CONVERSATION_TURN', payload: result.conversationTurn });
        dispatch({ type: 'SET_WS_PHASE', payload: 'question_ready' });
      } catch {
        scheduleReconnect();
      }
    }, delay);
  }, [controller]);

  useEffect(() => {
    if (!state.session) return;
    const toSave = {
      session: state.session,
      currentQuestion: state.currentQuestion,
      evaluationHistory: state.evaluationHistory,
      historyIndex: state.historyIndex,
      cardVisible: state.cardVisible,
      conversationTurn: state.conversationTurn,
      interviewMode: state.interviewMode,
    };
    try {
      sessionStorage.setItem('aiInterviewState', JSON.stringify(toSave));
    } catch {}
  }, [state.session, state.currentQuestion, state.evaluationHistory, state.historyIndex, state.cardVisible, state.conversationTurn, state.interviewMode]);

  const actions = useMemo<InterviewStoreActions>(() => {
    const fetchFinalReport = async () => {
      if (!stateRef.current.session) return;
      dispatch({ type: 'SET_LOADING', payload: true });
      try {
        const { interviewService } = await import('../services/interviewService');
        const report = await interviewService.getSummary(stateRef.current.session.session_id);
        dispatch({ type: 'SET_FINAL_REPORT', payload: report });
      } catch (error: any) {
        dispatch({ type: 'SET_ERROR', payload: error.message });
      }
    };

    return {
      startInterview: async ({ sessionId }) => {
        dispatch({ type: 'SET_LOADING', payload: true });
        try {
          sessionIdRef.current = sessionId;
          reconnectAttemptsRef.current = 0;
          clearReconnectTimer();
          const result = await controller.initInterviewViaWS(sessionId);

          wsOffRef.current?.();
          wsOffRef.current = interviewWebSocket.on('status', (data: any) => {
            if (data?.phase) {
              dispatch({ type: 'SET_WS_PHASE', payload: data.phase });
            }
          });
          closeOffRef.current?.();
          closeOffRef.current = interviewWebSocket.on('close', () => {
            if (stateRef.current.session?.status === 'completed') return;
            scheduleReconnect();
          });

          dispatch({ type: 'SET_SESSION', payload: result.session });
          dispatch({ type: 'SET_QUESTION', payload: result.firstQuestion });
          dispatch({ type: 'SET_CONVERSATION_TURN', payload: result.conversationTurn });
          dispatch({ type: 'SET_WS_PHASE', payload: 'question_ready' });
        } catch (error: any) {
          dispatch({ type: 'SET_ERROR', payload: error.message });
        }
      },

      cancelInterview: () => {
        wsOffRef.current?.();
        wsOffRef.current = null;
        closeOffRef.current?.();
        closeOffRef.current = null;
        clearReconnectTimer();
        reconnectAttemptsRef.current = 0;
        sessionIdRef.current = null;
        controller.cancelInterviewWS();
        dispatch({ type: 'RESET_STATE' });
      },

      fetchFinalReport,

      goToNextQuestion: async () => {
        dispatch({ type: 'SET_LOADING', payload: true });
        try {
          const nextQuestion = await controller.goToNextQuestion();
          dispatch({ type: 'SET_USER_ANSWER', payload: '' });
          dispatch({ type: 'SET_QUESTION', payload: nextQuestion });
          if (nextQuestion.phase) {
            dispatch({ type: 'SET_SESSION_PHASE', payload: nextQuestion.phase });
          }
        } catch (error: any) {
          dispatch({ type: 'SET_ERROR', payload: error.message });
        }
      },

      submitAnswer: async (answer) => {
        if (!answer || !answer.trim()) {
          dispatch({ type: 'SET_ERROR', payload: 'Please enter an answer before submitting.' });
          return;
        }
        dispatch({ type: 'SET_EVALUATING', payload: true });
        dispatch({ type: 'SET_USER_ANSWER', payload: answer });
        try {
          const result = await controller.submitAnswerViaWS({ answer });
          dispatch({ type: 'SET_EVALUATION', payload: result });

          const currentQ = stateRef.current.currentQuestion;
          const entry: EvaluationHistoryEntry = {
            questionNumber: result.question_number,
            question: currentQ?.question || '',
            answer: answer,
            score: result.score,
            technicalScore: result.technical_score,
            communicationScore: result.communication_score,
            strengths: result.strengths || [],
            weaknesses: result.weaknesses || [],
            feedback: result.evaluation || '',
            conversationTurn: result.conversationTurn || '',
          };
          dispatch({ type: 'PUSH_EVALUATION', payload: entry });

          if (result.interview_status === 'completed') {
            dispatch({ type: 'SET_WS_PHASE', payload: 'idle' });
            dispatch({ type: 'SET_CONVERSATION_TURN', payload: '' });
            const sess = stateRef.current.session;
            if (sess) {
              dispatch({ type: 'SET_SESSION', payload: { ...sess, status: 'completed' as InterviewStatus } });
            }
          } else {
            const snap = controller.getSession();
            if (snap.currentQuestion) {
              dispatch({ type: 'SET_QUESTION', payload: snap.currentQuestion });
            }
            dispatch({ type: 'SET_USER_ANSWER', payload: '' });
            dispatch({ type: 'SET_EVALUATION', payload: null as unknown as AnswerEvaluation });
            dispatch({ type: 'SET_CONVERSATION_TURN', payload: result.conversationTurn || '' });
          }
        } catch (error: any) {
          dispatch({ type: 'SET_ERROR', payload: error.message });
        }
      },

      updateAnswer: (answer: string) => {
        dispatch({ type: 'SET_USER_ANSWER', payload: answer });
      },

      clearError: () => {
        dispatch({ type: 'SET_ERROR', payload: '' });
      },

      goToPrevEvaluation: () => {
        const current = stateRef.current;
        if (current.historyIndex > 0) {
          dispatch({ type: 'SET_HISTORY_INDEX', payload: current.historyIndex - 1 });
        }
      },

      goToNextEvaluation: () => {
        const current = stateRef.current;
        if (current.historyIndex < current.evaluationHistory.length - 1) {
          dispatch({ type: 'SET_HISTORY_INDEX', payload: current.historyIndex + 1 });
        }
      },

      toggleCard: () => {
        dispatch({ type: 'TOGGLE_CARD' });
      },
    };
  }, []);

  return (
    <InterviewContext.Provider value={{ state, dispatch, actions }}>
      {children}
    </InterviewContext.Provider>
  );
}

// ========== HOOK ==========

export function useInterviewStore() {
  const context = useContext(InterviewContext);
  if (context === undefined) {
    throw new Error('useInterviewStore must be used within an InterviewProvider');
  }
  return context;
}