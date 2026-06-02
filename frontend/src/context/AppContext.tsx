import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { getProblems, getContexts } from '../api/client';
import type { Problem, Context, GeneratedEmail } from '../types';

interface AppState {
  problems: Problem[];
  contexts: Context[];
  emails: GeneratedEmail[];
  hydrated: boolean;
  lastSync: string | null;
}

type Action =
  | { type: 'ADD_PROBLEM'; payload: Problem }
  | { type: 'ADD_CONTEXT'; payload: Context }
  | { type: 'ADD_EMAIL'; payload: GeneratedEmail }
  | { type: 'LOAD_STATE'; payload: AppState }
  | { type: 'SYNC_STATE'; payload: { problems: Problem[]; contexts: Context[] } }
  | { type: 'CLEAR_ALL' };

const initialState: AppState = {
  problems: [],
  contexts: [],
  emails: [],
  hydrated: false,
  lastSync: null,
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'ADD_PROBLEM':
      return { ...state, problems: [action.payload, ...state.problems] };
    case 'ADD_CONTEXT':
      return { ...state, contexts: [action.payload, ...state.contexts] };
    case 'ADD_EMAIL':
      return { ...state, emails: [action.payload, ...state.emails] };
    case 'LOAD_STATE':
      return { ...action.payload, hydrated: true };
    case 'SYNC_STATE': {
      // Merge backend data with frontend cache, preferring backend for problems/contexts
      // but keeping emails (since backend doesn't have a list endpoint for them)
      const backendProblems = action.payload.problems.map(normalizeProblem);
      const backendContexts = action.payload.contexts.map(normalizeContext);

      return {
        ...state,
        problems: backendProblems,
        contexts: backendContexts,
        lastSync: new Date().toISOString(),
        hydrated: true,
      };
    }
    case 'CLEAR_ALL':
      return { ...initialState, hydrated: true };
    default:
      return state;
  }
}

// Normalize backend Problem shape to frontend shape
function normalizeProblem(p: Problem): Problem {
  // Backend GET /problems/{id} returns { id, problem_name, system, ... }
  // Frontend expects { problem_id, snapshot: { problem_name, system }, fullData, createdAt }
  return {
    ...p,
    problem_id: p.problem_id ?? p.id,
    snapshot: p.snapshot ?? {
      problem_name: p.problem_name || 'Untitled',
      system: p.system || '',
    },
    fullData: p.fullData ?? {
      problem_name: p.problem_name || '',
      core_problem: p.core_problem || '',
      system: p.system || '',
      causal_mechanism: p.causal_mechanism || '',
      failure_mode_A: p.failure_mode_A || '',
      failure_mode_B: p.failure_mode_B || '',
      failure_mode_A_mechanism: p.failure_mode_A_mechanism || '',
      failure_mode_B_mechanism: p.failure_mode_B_mechanism || '',
      contradiction: p.contradiction || '',
      business_impact: p.business_impact || '',
      solution_mechanism: p.solution_mechanism || '',
      solution_actor: p.solution_actor || '',
    },
    createdAt: p.createdAt ?? p.created_at ?? new Date().toISOString(),
  };
}

// Normalize backend Context shape to frontend shape
function normalizeContext(c: Context): Context {
  return {
    ...c,
    context_id: c.context_id ?? c.id,
    problem_id: c.problem_id ?? '',
    snapshot: c.snapshot ?? {
      industry: c.industry || '',
      company_size: c.company_size || '',
      decision_actor: c.decision_actor || '',
      constraints: c.constraints || [],
      extra: c.extra || '',
    },
    createdAt: c.createdAt ?? c.created_at ?? new Date().toISOString(),
  };
}

type ContextValue = {
  state: AppState;
  dispatch: React.Dispatch<Action>;
  syncWithBackend: () => Promise<void>;
  clearCache: () => void;
} | null;

const AppContext = createContext<ContextValue>(null);

const STORAGE_KEY = 'email_pipeline_state';

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Load from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        dispatch({ type: 'LOAD_STATE', payload: parsed });
      } catch {
        localStorage.removeItem(STORAGE_KEY);
        dispatch({ type: 'LOAD_STATE', payload: initialState });
      }
    } else {
      dispatch({ type: 'LOAD_STATE', payload: initialState });
    }
  }, []);

  // Persist to localStorage on change
  useEffect(() => {
    if (state.hydrated) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
  }, [state]);

  // Sync with backend - fetch fresh data
  const syncWithBackend = useCallback(async () => {
    try {
      const [problems, contexts] = await Promise.all([
        getProblems().catch(() => []),
        getContexts().catch(() => []),
      ]);
      dispatch({ type: 'SYNC_STATE', payload: { problems, contexts } });
    } catch (err) {
      console.error('Sync failed:', err);
    }
  }, []);

  // Clear all cached data
  const clearCache = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    dispatch({ type: 'CLEAR_ALL' });
  }, []);

  return (
    <AppContext.Provider value={{ state, dispatch, syncWithBackend, clearCache }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}