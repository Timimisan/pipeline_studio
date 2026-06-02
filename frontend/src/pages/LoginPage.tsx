import { useState, useRef, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mail, Lock, Zap, AlertCircle, ArrowRight, Loader2, Globe } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [oauthLoading, setOauthLoading] = useState(false);
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();
  const isNavigating = useRef(false);

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
          credentials: 'include',                 // send cookie if present
          headers: {
            Authorization: `Bearer ${token}`,     // send token if using BearerTransport
          },
        });

        if (!res.ok) throw new Error('Invalid or expired session');

        const user = await res.json();

        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));

        // Clean URL so token doesn't sit in browser history
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
    e.stopPropagation();
    setError('');
    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err?.message || 'Login failed');
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

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)]">
      <div className="w-full max-w-md px-6">
        <div className="flex items-center justify-center gap-3 mb-10">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Pipeline</h1>
            <p className="text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-widest">Studio</p>
          </div>
        </div>

        <div className="form-card">
          <div className="form-card-header text-center">
            <h2 className="text-xl font-bold text-white">Welcome Back</h2>
            <p className="text-sm text-slate-500 mt-1">Sign in to your account</p>
          </div>

          {error && (
            <div className="mx-8 mt-4">
              <div className="alert-premium alert-error">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <div className="flex flex-col gap-1">
                  <span>{error}</span>
                  <span className="text-[11px] opacity-80">
                    If you recently registered, check your inbox for a verification email before signing in.
                  </span>
                </div>
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
                <span className="px-2 bg-[var(--bg-primary)] text-[var(--text-muted)]">or continue with email</span>
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
              </div>

              <div className="flex items-center justify-between">
                <Link
                  to="/forgot-password"
                  className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  Forgot password?
                </Link>
              </div>

              <button
                type="submit"
                disabled={!!isLoading}
                className="btn-premium btn-premium-primary w-full justify-center"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="form-card-footer justify-center">
            <p className="text-sm text-slate-500">
              Don't have an account?{' '}
              <Link to="/register" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}