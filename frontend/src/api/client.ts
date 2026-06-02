import type {
  CreateProblemRequest,
  ProblemResponse,
  CreateContextRequest,
  ContextResponse,
  RunPipelineRequest,
  PipelineResult,
  PipelineTrace,
  AnalyticsData,
  EmailAnalytics,
  Problem,
  Context,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ============================================================
// ERROR MAPPING (fastapi-users error codes)
// ============================================================

const ERROR_MESSAGES: Record<string, string> = {
  // Login errors
  LOGIN_BAD_CREDENTIALS: 'Invalid email or password. Please check your credentials and try again.',
  LOGIN_USER_NOT_VERIFIED: 'Please verify your email address before logging in.',
  LOGIN_USER_NOT_ACTIVE: 'Your account has been deactivated. Contact support for help.',

  // Register errors
  REGISTER_USER_ALREADY_EXISTS: 'An account with this email already exists. Try logging in instead.',
  REGISTER_INVALID_PASSWORD: 'Password does not meet security requirements.',

  // Reset/verify errors
  RESET_PASSWORD_BAD_TOKEN: 'Invalid or expired password reset token.',
  VERIFY_USER_BAD_TOKEN: 'Invalid or expired verification token.',
  UPDATE_USER_EMAIL_ALREADY_EXISTS: 'This email is already associated with another account.',
  UPDATE_USER_INVALID_PASSWORD: 'Current password is incorrect.',
};

function parseErrorResponse(data: any, fallback: string): string {
  // Case 1: fastapi-users returns { detail: "LOGIN_BAD_CREDENTIALS" } or { detail: "Error message" }
  if (data?.detail) {
    const detail = data.detail;

    // If detail is a string
    if (typeof detail === 'string') {
      // Check if it's a known error code
      if (ERROR_MESSAGES[detail]) {
        return ERROR_MESSAGES[detail];
      }
      // Check if error code is embedded in the string
      for (const [code, msg] of Object.entries(ERROR_MESSAGES)) {
        if (detail.includes(code)) {
          return msg;
        }
      }
      return detail;
    }

    // If detail is an array (validation errors)
    if (Array.isArray(detail)) {
      const messages: string[] = [];
      for (const err of detail) {
        const field = err.loc?.[err.loc.length - 1] || 'field';
        const msg = err.msg || 'Invalid value';

        // User-friendly translations
        if (msg.toLowerCase().includes('email') && msg.toLowerCase().includes('valid')) {
          messages.push('Please enter a valid email address.');
        } else if (msg.toLowerCase().includes('password') && msg.toLowerCase().includes('at least')) {
          messages.push('Password must be at least 8 characters.');
        } else if (msg.toLowerCase().includes('already exists') || msg.toLowerCase().includes('already registered')) {
          messages.push('An account with this email already exists.');
        } else {
          messages.push(`${field}: ${msg}`);
        }
      }
      return messages.join(' ') || 'Please check your input and try again.';
    }
  }

  // Case 2: Generic error object
  if (data?.message && typeof data.message === 'string') {
    return data.message;
  }

  return fallback;
}

// ============================================================
// AUTH
// ============================================================

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

export async function login(email: string, password: string): Promise<User> {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  console.log('[client.login] Sending login for:', email);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    credentials: 'include',
    body: formData,
  });

  console.log('[client.login] Response status:', res.status);

  if (!res.ok) {
    let errorDetail = 'Login failed';
    try {
      const errorData = await res.json();
      console.error('[client.login] Error response:', errorData);
      errorDetail = parseErrorResponse(errorData, `Login failed (HTTP ${res.status})`);
    } catch {
      const text = await res.text();
      console.error('[client.login] Raw error:', text);
      errorDetail = parseErrorResponse({ detail: text }, `Login failed (HTTP ${res.status})`);
    }
    throw new Error(errorDetail);
  }

  // 204 No Content = cookie set successfully, now fetch user data
  console.log('[client.login] Login succeeded (204), fetching current user...');
  return getCurrentUser();
}

export async function register(email: string, password: string): Promise<User> {
  console.log('[client.register] Sending register for:', email);

  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });

  console.log('[client.register] Response status:', res.status);

  if (!res.ok) {
    let errorDetail = 'Registration failed';
    try {
      const errorData = await res.json();
      console.error('[client.register] Error response:', errorData);
      errorDetail = parseErrorResponse(errorData, `Registration failed (HTTP ${res.status})`);
    } catch {
      const text = await res.text();
      console.error('[client.register] Raw error:', text);
      errorDetail = parseErrorResponse({ detail: text }, `Registration failed (HTTP ${res.status})`);
    }
    throw new Error(errorDetail);
  }

  const user = await res.json();
  console.log('[client.register] Success:', user);

  // Auto-login after registration
  await login(email, password);
  return user;
}

export async function logout(): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  });

  if (!res.ok) {
    console.warn('[client.logout] Logout returned non-OK status:', res.status);
  }
}

export async function getCurrentUser(): Promise<User> {
  const res = await fetch(`${API_BASE}/users/me`, {
    credentials: 'include',
  });

  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('UNAUTHORIZED');
    }
    throw new Error(`Failed to fetch user (HTTP ${res.status})`);
  }

  return res.json();
}

// ============================================================
// API CLIENT
// ============================================================

async function api<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (res.status === 401) {
    throw new Error('UNAUTHORIZED');
  }
  if (!res.ok) {
    let errorText = `API Error (${res.status})`;
    try {
      const errorData = await res.json();
      errorText = parseErrorResponse(errorData, errorText);
    } catch {
      const text = await res.text();
      if (text) errorText = text;
    }
    throw new Error(errorText);
  }

  return res.json();
}

// ─── PROBLEMS ───
export const createProblem = (data: CreateProblemRequest) =>
  api<ProblemResponse>('/api/problems', { method: 'POST', body: JSON.stringify(data) });

export const getProblems = () =>
  api<Problem[]>('/api/problems');

export const getProblem = (id: string) =>
  api<Problem>(`/api/problems/${id}`);

// ─── CONTEXTS ───
export const createContext = (data: CreateContextRequest) =>
  api<ContextResponse>('/api/contexts', { method: 'POST', body: JSON.stringify(data) });

export const getContexts = () =>
  api<Context[]>('/api/contexts');

export const getContext = (id: string) =>
  api<Context>(`/api/contexts/${id}`);

// ─── PIPELINE ───
export const runPipeline = (data: RunPipelineRequest) =>
  api<PipelineResult>('/api/run', { method: 'POST', body: JSON.stringify(data) });

export const runPipelineStream = (
  data: RunPipelineRequest,
  onMessage: (trace: PipelineTrace) => void,
  onComplete: (result: PipelineResult) => void,
  onError: (error: string) => void,
) => {
  const abortController = new AbortController();

  fetch(`${API_BASE}/api/run-stream`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    signal: abortController.signal,
  }).then(async (response) => {
    if (response.status === 401) {
      onError('UNAUTHORIZED');
      return;
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      onError('No response body');
      return;
    }

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            abortController.abort();
            return;
          }

          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'trace_update') {
              onMessage(parsed.data as PipelineTrace);
            } else if (parsed.type === 'complete') {
              onComplete(parsed.data as PipelineResult);
            } else if (parsed.type === 'error') {
              const msg = parsed.traceback
                ? `${parsed.message}\n\nTraceback:\n${parsed.traceback}`
                : parsed.message;
              onError(msg);
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', data);
          }
        }
      }
    }
  }).catch(err => {
    onError(err.message);
  });

  return () => abortController.abort();
};

// ─── ANALYTICS ───
export const getAnalytics = () =>
  api<AnalyticsData>('/api/analytics');

export const getEmailAnalytics = (contextId: string) =>
  api<EmailAnalytics>(`/api/analytics/email/${contextId}`);

// ─── DAILY ANALYTICS ───
export interface DailyAnalytics {
  day: string;
  date: string;
  latency: number;
  cost: number;
  retries: number;
  emails: number;
}

export const getDailyAnalytics = () =>
  api<DailyAnalytics[]>('/api/analytics/daily');