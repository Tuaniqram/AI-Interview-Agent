import React, { createContext, useContext, useEffect, useReducer, useCallback } from 'react';
import { isClaimPending } from '../types/candidate';
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
  /** Resolves `{ claimPending: true }` when the email already has guest activity (finish via emailed link). */
  register: (req: CandidateRegisterRequest) => Promise<{ claimPending: boolean; message?: string }>;
  claimAccount: (data: { token: string; password: string; name?: string }) => Promise<void>;
  /** Re-read the profile (e.g. after the email was verified in this browser). */
  refreshProfile: () => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
  updateProfile: (profile: CandidateProfile) => void;
  sendVerification: () => Promise<void>;
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
    if (isClaimPending(res)) return { claimPending: true, message: res.message };
    localStorage.setItem('candidate_tokens', JSON.stringify(res.tokens));
    dispatch({ type: 'LOGIN_SUCCESS', payload: res });
    return { claimPending: false };
  }, []);

  const claimAccount = useCallback(async (data: { token: string; password: string; name?: string }) => {
    const res = await candidateService.claimAccount(data);
    localStorage.setItem('candidate_tokens', JSON.stringify(res.tokens));
    dispatch({ type: 'LOGIN_SUCCESS', payload: res });
  }, []);

  const refreshProfile = useCallback(async () => {
    if (!localStorage.getItem('candidate_tokens')) return;
    try {
      dispatch({ type: 'UPDATE_PROFILE', payload: await candidateService.me() });
    } catch { /* keep the current profile */ }
  }, []);

  const googleLogin = useCallback(async (credential: string) => {
    const res = await candidateService.googleLogin(credential);
    localStorage.setItem('candidate_tokens', JSON.stringify(res.tokens));
    dispatch({ type: 'LOGIN_SUCCESS', payload: res });
  }, []);

  const updateProfile = useCallback((profile: CandidateProfile) => {
    dispatch({ type: 'UPDATE_PROFILE', payload: profile });
  }, []);

  const sendVerification = useCallback(async () => {
    await candidateService.sendVerification();
  }, []);

  return (
    <CandidateAuthContext.Provider value={{ ...state, login, register, claimAccount, refreshProfile, googleLogin, logout, updateProfile, sendVerification }}>
      {children}
    </CandidateAuthContext.Provider>
  );
}

export function useCandidateAuth() {
  const ctx = useContext(CandidateAuthContext);
  if (!ctx) throw new Error('useCandidateAuth must be used within CandidateAuthProvider');
  return ctx;
}
