import React, { createContext, useContext, useEffect, useReducer, useCallback } from 'react';
import type { AuthState, User, Tokens, OrgMembership, LoginRequest, RegisterRequest } from '../types/auth';
import { authService } from '../services/authService';
import { apiClient } from '../services/apiClient';

type AuthAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; tokens: Tokens; memberships: OrgMembership[] } }
  | { type: 'LOGOUT' }
  | { type: 'UPDATE_USER'; payload: User }
  | { type: 'SET_MEMBERSHIPS'; payload: OrgMembership[] };

const initialState: AuthState = {
  user: null,
  tokens: null,
  memberships: [],
  isAuthenticated: false,
  isLoading: true,
};

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        tokens: action.payload.tokens,
        memberships: action.payload.memberships,
        isAuthenticated: true,
        isLoading: false,
      };
    case 'LOGOUT':
      return { ...initialState, isLoading: false };
    case 'UPDATE_USER':
      return { ...state, user: action.payload };
    case 'SET_MEMBERSHIPS':
      return { ...state, memberships: action.payload };
    default:
      return state;
  }
}

interface AuthContextType extends AuthState {
  login: (req: LoginRequest) => Promise<void>;
  register: (req: RegisterRequest) => Promise<void>;
  logout: () => void;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_tokens');
    localStorage.removeItem('active_org_id');
    dispatch({ type: 'LOGOUT' });
  }, []);

  useEffect(() => {
    apiClient.onAuthFailure = logout;
    return () => {
      apiClient.onAuthFailure = null;
    };
  }, [logout]);

  useEffect(() => {
    const stored = localStorage.getItem('auth_tokens');
    if (stored) {
      try {
        const tokens = JSON.parse(stored);
        authService.me().then((res) => {
          dispatch({
            type: 'LOGIN_SUCCESS',
            payload: {
              user: res.user,
              tokens,
              memberships: res.memberships,
            },
          });
        }).catch(() => {
          localStorage.removeItem('auth_tokens');
          dispatch({ type: 'SET_LOADING', payload: false });
        });
      } catch {
        localStorage.removeItem('auth_tokens');
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    } else {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  const login = useCallback(async (req: LoginRequest) => {
    const res = await authService.login(req);
    localStorage.setItem('auth_tokens', JSON.stringify(res.tokens));
    if (res.memberships.length > 0) {
      localStorage.setItem('active_org_id', res.memberships[0].org_id);
    }
    dispatch({ type: 'LOGIN_SUCCESS', payload: res });
  }, []);

  const register = useCallback(async (req: RegisterRequest) => {
    const res = await authService.register(req);
    localStorage.setItem('auth_tokens', JSON.stringify(res.tokens));
    if (res.memberships.length > 0) {
      localStorage.setItem('active_org_id', res.memberships[0].org_id);
    }
    dispatch({ type: 'LOGIN_SUCCESS', payload: res });
  }, []);

  const updateUser = useCallback((user: User) => {
    dispatch({ type: 'UPDATE_USER', payload: user });
  }, []);

  return (
    <AuthContext.Provider
      value={{ ...state, login, register, logout, updateUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
