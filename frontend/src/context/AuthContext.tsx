import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { login as apiLogin, register as apiRegister, logout as apiLogout, getCurrentUser } from '../api/client';
import type { User } from '../api/client';

// ─── State & Reducer ───

interface AuthState {
  user: User | null;
  loading: boolean;
  hydrated: boolean;
}

type AuthAction =
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'HYDRATED' };

const initialState: AuthState = {
  user: null,
  loading: true,
  hydrated: false,
};

function reducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'SET_USER':
      return { ...state, user: action.payload, loading: false };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'HYDRATED':
      return { ...state, hydrated: true, loading: false };
    default:
      return state;
  }
}

// ─── Context (type assertion avoids generic syntax issues) ───

const AuthContext = createContext(null as {
  user: User | null;
  isLoading: boolean;
  hydrated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
} | null);

// ─── Provider ───

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const checkAuth = useCallback(async () => {
    try {
      const user = await getCurrentUser();
      dispatch({ type: 'SET_USER', payload: user });
    } catch {
      dispatch({ type: 'SET_USER', payload: null });
    } finally {
      dispatch({ type: 'HYDRATED' });
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (email: string, password: string) => {
    console.log('[AuthContext.login] called with:', email);
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const user = await apiLogin(email, password);
      console.log('[AuthContext.login] apiLogin succeeded:', user);
      dispatch({ type: 'SET_USER', payload: user });
    } catch (err) {
      console.error('[AuthContext.login] apiLogin failed:', err);
      dispatch({ type: 'SET_LOADING', payload: false });
      throw err;
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    console.log('[AuthContext.register] called with:', email);
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const user = await apiRegister(email, password);
      console.log('[AuthContext.register] apiRegister succeeded:', user);
      dispatch({ type: 'SET_USER', payload: user });
    } catch (err) {
      console.error('[AuthContext.register] apiRegister failed:', err);
      dispatch({ type: 'SET_LOADING', payload: false });
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      await apiLogout();
    } catch {
      // ignore
    } finally {
      dispatch({ type: 'SET_USER', payload: null });
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user: state.user,
        isLoading: state.loading,
        hydrated: state.hydrated,
        login,
        register,
        logout,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ─── Hook ───

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}