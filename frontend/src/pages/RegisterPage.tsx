import { useState, useRef, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, UserPlus, AlertCircle, ArrowRight, Loader2, CheckCircle, Inbox, Globe } from 'lucide-react';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRegistered, setIsRegistered] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const isNavigating = useRef(false);
  const navigate = useNavigate();

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // ── OAuth callback: grab token, verify with /users/me, then go to dashboard ──
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');

    if (!token) return;

    const verifyAndRedirect = async () => {
      setOauthLoading(true);
      try {
        const res = await fetch(`${API_BASE}/users/me`, {
          credentials: 'include',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error('Invalid or expired session');

        const user = await res.json();

        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));

        window.history.replaceState({}, document.title, window.location.pathname);
        navigate('/dashboard', { replace: true });
      } catch (err: any) {
        setError(err?.message || 'OAuth login failed');
        setOauthLoading(false);
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    };

    verifyAndRedirect();
  }, [navigate, API_BASE]);
  // ───────────────────────────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setResendSuccess(false);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        let msg = 'Registration failed';
        try {
          const data = await res.json();
          msg = data.detail || msg;
          if (msg === 'REGISTER_USER_ALREADY_EXISTS') {
            msg = 'An account with this email already exists. Try logging in instead.';
          }
          if (msg === 'REGISTER_INVALID_PASSWORD') {
            msg = 'Password does not meet security requirements.';
          }
        } catch {
          const text = await res.text();
          if (text) msg = text;
        }
        throw new Error(msg);
      }

      setIsRegistered(true);
    } catch (err: any) {
      setError(err?.message || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    setResendLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/auth/request-verify-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        let msg = 'Failed to resend';
        try {
          const data = await res.json();
          msg = data.detail || msg;
        } catch {}
        throw new Error(msg);
      }
      setResendSuccess(true);
    } catch (err: any) {
      setError(err?.message || 'Failed to resend verification email. Please try again.');
    } finally {
      setResendLoading(false);
    }
  };

  const handleGoogleOAuth = async () => {
    if (isNavigating.current) return;
    isNavigating.current = true;

    const res = await fetch(
      `${API_BASE}/auth/google/authorize`,
      {
        credentials: "include",
      }
    );

    const data = await res.json();
    window.location.href = data.authorization_url;
  };

  if (oauthLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
          <p className="text-sm text-slate-400">Completing sign-in…</p>
        </div>
      </div>
    );
  }

  if (isRegistered) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)]">
        <div className="w-full max-w-md px-6">
          <div className="flex items-center justify-center gap-3 mb-10">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <UserPlus className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">Pipeline</h1>
              <p className="text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-widest">Studio</p>
            </div>
          </div>

          <div className="form-card text-center">
            <div className="form-card-header">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-500/20">
                <Inbox className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-bold text-white">Check Your Inbox</h2>
              <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                We sent a verification link to{' '}
                <span className="text-indigo-400 font-medium">{email}</span>.
                Please click the link in that email to activate your account.
              </p>
            </div>

            <div className="form-card-body space-y-4">
              {resendSuccess && (
                <div className="alert-premium alert-success flex items-center gap-2 justify-center text-sm">
                  <CheckCircle className="w-4 h-4 shrink-0" />
                  Verification email resent successfully
                </div>
              )}

              {error && (
                <div className="alert-premium alert-error flex items-center gap-2 justify-center text-sm">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}

              <button
                onClick={handleResend}
                disabled={resendLoading}
                className="btn-premium w-full justify-center bg-white/5 hover:bg-white/10 text-white border border-white/10 transition-all"
              >
                {resendLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Resending…
                  </>
                ) : (
                  <>
                    <Mail className="w-4 h-4" />
                    Resend Verification Email
                  </>
                )}
              </button>

              <button
                onClick={() => navigate('/login')}
                className="btn-premium btn-premium-primary w-full justify-center"
              >
                <ArrowRight className="w-4 h-4" />
                Go to Sign In
              </button>
            </div>

            <div className="form-card-footer justify-center">
              <p className="text-xs text-slate-500">
                Wrong email?{' '}
                <button
                  onClick={() => setIsRegistered(false)}
                  className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                >
                  Go back
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)]">
      <div className="w-full max-w-md px-6">
        <div className="flex items-center justify-center gap-3 mb-10">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <UserPlus className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Pipeline</h1>
            <p className="text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-widest">Studio</p>
          </div>
        </div>

        <div className="form-card">
          <div className="form-card-header text-center">
            <h2 className="text-xl font-bold text-white">Create Account</h2>
            <p className="text-sm text-slate-500 mt-1">Get started with Pipeline Studio</p>
          </div>

          {error && (
            <div className="mx-8 mt-4">
              <div className="alert-premium alert-error">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            </div>
          )}

          <div className="form-card-body">
            <button
              type="button"
              onClick={handleGoogleOAuth}
              className="btn-premium w-full justify-center bg-white/5 hover:bg-white/10 text-white border border-white/10 transition-all"
            >
              <Globe className="w-4 h-4 text-blue-400" />
              Continue with Google
            </button>

            <div className="relative my-5">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-[var(--border-subtle)]" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-2 bg-[var(--bg-primary)] text-[var(--text-muted)]">or sign up with email</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="input-label-premium">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                  <input
                    type="email"
                    className="input-premium pl-10"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="input-label-premium">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                  <input
                    type="password"
                    className="input-premium pl-10"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                </div>
                <p className="text-[10px] text-slate-600 mt-1">Minimum 8 characters</p>
              </div>

              <div>
                <label className="input-label-premium">Confirm Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                  <input
                    type="password"
                    className="input-premium pl-10"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="btn-premium btn-premium-primary w-full justify-center"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating account…
                  </>
                ) : (
                  <>
                    Create Account
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="form-card-footer justify-center">
            <p className="text-sm text-slate-500">
              Already have an account?{' '}
              <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}