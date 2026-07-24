import React, { createContext, useContext, useEffect, useReducer, useCallback } from 'react';
import type { CandidateProfile, CandidateTokens, CandidateLoginRequest, CandidateRegisterRequest } from '../types/candidate';
import { candidateService } from '../services/candidateService';

type AuthAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'LOGIN_SUCCESS'; payload: { candidate: CandidateProfile; tokens: CandidateTokens } }
  | { type: 'LOGOUT' }
  | { type: 'UPDATE_PROFILE'; payload: CandidateProfile };

interface CandidateAuthState {
  candidate: CandidateProfile | null;
  tokens: CandidateTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const initialState: CandidateAuthState = {
  candidate: null,
  tokens: null,
  isAuthenticated: false,
  isLoading: true,
};

function authReducer(state: CandidateAuthState, action: AuthAction): CandidateAuthState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        candidate: action.payload.candidate,
        tokens: action.payload.tokens,
        isAuthenticated: true,
        isLoading: false,
      };
    case 'LOGOUT':
      return { ...initialState, isLoading: false };
    case 'UPDATE_PROFILE':
      return { ...state, candidate: action.payload };
    default:
      return state;
  }
}

interface CandidateAuthContextType extends CandidateAuthState {
  login: (req: CandidateLoginRequest) => Promise<void>;
  register: (req: CandidateRegisterRequest) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
  updateProfile: (profile: CandidateProfile) => void;
}

const CandidateAuthContext = createContext<CandidateAuthContextType | undefined>(undefined);

export function CandidateAuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  const logout = useCallback(() => {
    localStorage.removeItem('candidate_tokens');
    dispatch({ type: 'LOGOUT' });
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem('candidate_tokens');
    if (stored) {
      try {
        const tokens = JSON.parse(stored);
        candidateService.me().then((profile) => {
          dispatch({ type: 'LOGIN_SUCCESS', payload: { candidate: profile, tokens } });
        }).catch(() => {
          localStorage.removeItem('candidate_tokens');
          dispatch({ type: 'SET_LOADING', payload: false });
        });
      } catch {
        localStorage.removeItem('candidate_tokens');
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    } else {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  const login = useCallback(async (req: CandidateLoginRequest) => {
    const res = await candidateService.login(req);
    localStorage.setItem('candidate_tokens', JSON.stringify(res.tokens));
    dispatch({ type: 'LOGIN_SUCCESS', payload: res });
  }, []);

  const register = useCallback(async (req: CandidateRegisterRequest) => {
    const res = await candidateService.register(req);
    localStorage.setItem('candidate_tokens', JSON.stringify(res.tokens));
    dispatch({ type: 'LOGIN_SUCCESS', payload: res });
  }, []);

  const googleLogin = useCallback(async (credential: string) => {
    const res = await candidateService.googleLogin(credential);
    localStorage.setItem('candidate_tokens', JSON.stringify(res.tokens));
    dispatch({ type: 'LOGIN_SUCCESS', payload: res });
  }, []);

  const updateProfile = useCallback((profile: CandidateProfile) => {
    dispatch({ type: 'UPDATE_PROFILE', payload: profile });
  }, []);

  return (
    <CandidateAuthContext.Provider value={{ ...state, login, register, googleLogin, logout, updateProfile }}>
      {children}
    </CandidateAuthContext.Provider>
  );
}

export function useCandidateAuth() {
  const ctx = useContext(CandidateAuthContext);
  if (!ctx) throw new Error('useCandidateAuth must be used within CandidateAuthProvider');
  return ctx;
}
