/**
 * Interview Store - React Context for global interview state
 * Centralized state management with context API
 */

import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { 
  InterviewSession, 
  Question, 
  AnswerEvaluation, 
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
  | { type: 'SET_QUESTION'; payload: Question }
  | { type: 'SET_USER_ANSWER'; payload: string }
  | { type: 'SET_EVALUATION'; payload: AnswerEvaluation }
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
  finalReport: null,
  interviewMode: 'avatar',
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
      return {
        ...state,
        session: action.payload,
        isLoading: false,
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

    case 'SET_FINAL_REPORT':
      return {
        ...state,
        finalReport: action.payload,
      };

    case 'SET_INTERVIEW_MODE':
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
  clearError: () => void;
}

// ========== PROVIDER ==========

interface InterviewProviderProps {
  children: ReactNode;
}

export function InterviewProvider({ children }: InterviewProviderProps) {
  const [state, dispatch] = useReducer(interviewReducer, initialState);
  const controller = interviewController;

  // Actions with controller integration
  const actions: InterviewStoreActions = {
    startInterview: async (params) => {
      dispatch({ type: 'SET_LOADING', payload: true });
      try {
        if (params.mode) {
          dispatch({ type: 'SET_INTERVIEW_MODE', payload: params.mode as InterviewMode });
        }
        const result = await controller.startInterview(params);
        console.log('[Store] QUESTION RECEIVED:', result.firstQuestion);
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

    fetchFinalReport: async () => {
      if (!state.session) return;
      
      dispatch({ type: 'SET_LOADING', payload: true });
      try {
        const { interviewService } = await import('../services/interviewService');
        const report = await interviewService.getSummary(state.session.session_id);
        dispatch({ type: 'SET_FINAL_REPORT', payload: report });
      } catch (error: any) {
        dispatch({ type: 'SET_ERROR', payload: error.message });
      }
    },

    goToNextQuestion: async () => {
      dispatch({ type: 'SET_LOADING', payload: true });
      try {
        const nextQuestion = await controller.goToNextQuestion();
        console.log('[Store] QUESTION RECEIVED:', nextQuestion);
        // Clear previous answer so the next question renders fresh.
        dispatch({ type: 'SET_USER_ANSWER', payload: '' });
        dispatch({ type: 'SET_EVALUATION', payload: null as unknown as AnswerEvaluation });
        dispatch({ type: 'SET_QUESTION', payload: nextQuestion });
      } catch (error: any) {
        dispatch({ type: 'SET_ERROR', payload: error.message });
      }
    },

    submitAnswer: async (answer) => {
      // Only block truly empty answers. The backend LLM evaluator handles
      // short/long answers appropriately. A hard 50-char client gate would
      // reject valid intro-question responses (e.g. "Yes" / "Hi" / short name).
      if (!answer || !answer.trim()) {
        dispatch({ type: 'SET_ERROR', payload: 'Please enter an answer before submitting.' });
        return;
      }

      const payload = {
        answer,
        sessionId: state.session?.session_id,
        questionNumber: state.currentQuestion?.question_number,
      };
      console.log('[Store] SUBMIT ANSWER:', payload);

      dispatch({ type: 'SET_EVALUATING', payload: true });
      dispatch({ type: 'SET_USER_ANSWER', payload: answer });
      try {
        const evaluation = await controller.submitAnswer({ answer });
        console.log('[Store] EVALUATION RESULT:', evaluation);
        dispatch({ type: 'SET_EVALUATION', payload: evaluation });

        // If interview completed, fetch report
        if (evaluation.interview_status === 'completed') {
          console.log('[Store] Interview completed, fetching final report...');
          await actions.fetchFinalReport();
        } else {
          // Backend controls flow: if not completed, get next question
          console.log('[Store] Fetching next question...');
          await actions.goToNextQuestion();
        }
      } catch (error: any) {
        console.error('[Store] submitAnswer error:', error);
        dispatch({ type: 'SET_ERROR', payload: error.message });
      }
    },

    updateAnswer: (answer: string) => {
      dispatch({ type: 'SET_USER_ANSWER', payload: answer });
    },

    clearError: () => {
      dispatch({ type: 'SET_ERROR', payload: '' });
    },
  };

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