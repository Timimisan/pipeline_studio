import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Mail, PlusCircle, Home, FileText, BarChart3, Zap,
  ChevronRight, Sun, Moon, Upload, LogOut
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home, desc: 'Overview' },
    { path: '/problems/new', label: 'New Problem', icon: PlusCircle, desc: 'Create' },
    { path: '/emails', label: 'Emails', icon: Mail, desc: 'History' },
    { path: '/analytics', label: 'Analytics', icon: BarChart3, desc: 'Metrics' },
    { path: '/batch', label: 'Batch Import', icon: Upload, desc: 'CRM / CSV' },
  ];

  return (
    <div className="h-screen w-screen flex overflow-hidden bg-[var(--bg-primary)]">
      {/* Sidebar */}
      <aside className="w-[260px] sidebar-premium flex flex-col shrink-0">
        {/* Logo Area */}
        <div className="p-6 border-b border-[var(--border-subtle)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-[var(--text-primary)] tracking-tight">Pipeline</h1>
              <p className="text-[10px] text-[var(--text-muted)] font-medium uppercase tracking-widest">Studio</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
          <p className="px-3 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-widest mb-3">
            Navigation
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon className="shrink-0" />
                <span className="flex-1">{item.label}</span>
                {isActive && <ChevronRight className="w-4 h-4 text-indigo-400 shrink-0" />}
              </Link>
            );
          })}
        </nav>

        {/* User Section */}
        <div className="p-4 mx-4 mb-3 rounded-xl bg-[var(--bg-glass)] border border-[var(--border-subtle)]">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs font-bold text-white">
              {user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-[var(--text-primary)] truncate">
                {user?.email || 'User'}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-slate-400 hover:text-white transition-all border border-white/[0.04]"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>

        {/* Footer Info */}
        <div className="p-4 mx-4 mb-4 rounded-xl bg-[var(--bg-glass)] border border-[var(--border-subtle)]">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-[var(--status-online)] animate-pulse" />
            <span className="text-xs font-medium text-[var(--success)]">System Online</span>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] text-[var(--text-muted)] font-mono">Backend: FastAPI</p>
            <p className="text-[10px] text-[var(--text-muted)] font-mono">Model: GPT-5.4-mini</p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="header-premium shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              {navItems.find(n => n.path === location.pathname)?.label || 'Pipeline Studio'}
            </h2>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              {navItems.find(n => n.path === location.pathname)?.desc || 'Constrained Persuasion System'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="theme-toggle"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>
          </div>
        </header>

        {/* Scrollable Content */}
        <div className="content-area">
          <div className="max-w-6xl mx-auto animate-fade-in-up">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}