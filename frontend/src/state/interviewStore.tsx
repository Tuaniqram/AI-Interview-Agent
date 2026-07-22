/**
 * Interview Store - React Context for global interview state
 * Centralized state management with context API
 */

import React, { createContext, useContext, useReducer, useMemo, useRef, useEffect, ReactNode } from 'react';
import { 
  InterviewSession, 
  Question, 
  AnswerEvaluation, 
  EvaluationHistoryEntry,
  InterviewReport,
  InterviewMode
} from '../types/interview';
import { interviewController } from '../controllers/interviewController';

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
      if (action.payload.interview_mode) {
        localStorage.setItem('aiInterviewMode', action.payload.interview_mode);
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
  startInterview: (params: { companyId: number; jobRole: string; totalQuestions?: number; candidateName?: string; candidateEmail?: string; mode?: string }) => Promise<void>;
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

  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    if (!state.session) return;
    const toSave = {
      session: state.session,
      currentQuestion: state.currentQuestion,
      evaluationHistory: state.evaluationHistory,
      historyIndex: state.historyIndex,
      cardVisible: state.cardVisible,
      interviewMode: state.interviewMode,
    };
    try {
      sessionStorage.setItem('aiInterviewState', JSON.stringify(toSave));
    } catch {}
  }, [state.session, state.currentQuestion, state.evaluationHistory, state.historyIndex, state.cardVisible, state.interviewMode]);

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
      startInterview: async (params) => {
        dispatch({ type: 'SET_LOADING', payload: true });
        try {
          if (params.mode) {
            dispatch({ type: 'SET_INTERVIEW_MODE', payload: params.mode as InterviewMode });
          }
          const result = await controller.startInterview(params);
          dispatch({ type: 'SET_SESSION', payload: result.session });
          dispatch({ type: 'SET_QUESTION', payload: result.firstQuestion });
        } catch (error: any) {
          dispatch({ type: 'SET_ERROR', payload: error.message });
        }
      },

      cancelInterview: () => {
        controller.cancelInterview();
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
          const result = await controller.submitAnswer({ answer });
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
          };
          dispatch({ type: 'PUSH_EVALUATION', payload: entry });
          if (result.phase) {
            dispatch({ type: 'SET_SESSION_PHASE', payload: result.phase });
          }

          if (result.interview_status === 'completed') {
            await fetchFinalReport();
          } else {
            const nextQuestion = await controller.goToNextQuestion();
            dispatch({ type: 'SET_USER_ANSWER', payload: '' });
            dispatch({ type: 'SET_EVALUATION', payload: null as unknown as AnswerEvaluation });
            dispatch({ type: 'SET_QUESTION', payload: nextQuestion });
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