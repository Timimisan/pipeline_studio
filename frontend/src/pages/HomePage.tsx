import { Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Mail, FileText, ArrowRight, Activity, Zap, TrendingUp, Clock } from 'lucide-react';

export default function HomePage() {
  const { state } = useApp();

  const recentEmails = state.emails.slice(0, 5);
  const recentProblems = state.problems.slice(0, 5);

  const stats = [
    {
      label: 'Total Problems',
      value: state.problems.length,
      icon: FileText,
      color: 'from-blue-500 to-cyan-500',
      glow: 'shadow-blue-500/20',
    },
    {
      label: 'Total Contexts',
      value: state.contexts.length,
      icon: Activity,
      color: 'from-purple-500 to-pink-500',
      glow: 'shadow-purple-500/20',
    },
    {
      label: 'Emails Generated',
      value: state.emails.length,
      icon: Mail,
      color: 'from-emerald-500 to-teal-500',
      glow: 'shadow-emerald-500/20',
    },
  ];

  return (
    <div className="space-y-10">
      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Overview of your pipeline activity</p>
        </div>
        <Link
          to="/problems/new"
          className="btn-premium btn-premium-primary"
        >
          <Zap className="w-4 h-4" />
          New Problem
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="metric-card">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500 mb-1">{stat.label}</p>
                  <p className="text-3xl font-bold text-white tracking-tight">{stat.value}</p>
                </div>
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center shadow-lg ${stat.glow}`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 text-xs text-slate-600">
                <TrendingUp className="w-3 h-3 text-emerald-500" />
                <span className="text-emerald-400 font-medium">Active</span>
                <span className="text-slate-600">• Pipeline running</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Problems */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <FileText className="w-4 h-4 text-white" />
              </div>
              <h3 className="font-semibold text-white">Recent Problems</h3>
            </div>
            <Link to="/problems/new" className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors">
              + New Problem
            </Link>
          </div>

          <div className="space-y-3">
            {recentProblems.length === 0 ? (
              <div className="empty-state py-8">
                <div className="empty-state-icon">
                  <FileText className="w-8 h-8" />
                </div>
                <p className="text-sm font-medium text-slate-400">No problems created yet</p>
                <p className="text-xs text-slate-600 mt-1">Create your first problem to get started</p>
              </div>
            ) : (
              recentProblems.map(p => {
                const pid = p?.problem_id;
                const name = p?.snapshot?.problem_name || 'Untitled';
                const system = p?.snapshot?.system || '';
                if (pid == null) return null;
                return (
                  <Link
                    key={String(pid)}
                    to={`/problems/${pid}`}
                    className="list-card group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="min-w-0">
                        <h4 className="font-medium text-white group-hover:text-indigo-300 transition-colors truncate">
                          {name}
                        </h4>
                        <p className="text-xs text-slate-500 mt-1 truncate">{system}</p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-indigo-400 transition-colors shrink-0" />
                    </div>
                  </Link>
                );
              })
            )}
          </div>
        </div>

        {/* Recent Emails */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
                <Mail className="w-4 h-4 text-white" />
              </div>
              <h3 className="font-semibold text-white">Recent Emails</h3>
            </div>
            <Link to="/emails" className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors">
              View All
            </Link>
          </div>

          <div className="space-y-3">
            {recentEmails.length === 0 ? (
              <div className="empty-state py-8">
                <div className="empty-state-icon">
                  <Mail className="w-8 h-8" />
                </div>
                <p className="text-sm font-medium text-slate-400">No emails generated yet</p>
                <p className="text-xs text-slate-600 mt-1">Run a pipeline to generate emails</p>
              </div>
            ) : (
              recentEmails.map(e => (
                <Link
                  key={e?.id ?? Math.random()}
                  to={`/emails/${e?.id}`}
                  className="list-card group"
                >
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <h4 className="font-medium text-white group-hover:text-indigo-300 transition-colors truncate">
                        {e?.subject_line || 'No Subject'}
                      </h4>
                      <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {e?.createdAt ? new Date(e.createdAt).toLocaleDateString() : '—'}
                        </span>
                        <span>{e?.problemName || '—'}</span>
                        <span>{e?.contextName || '—'}</span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-indigo-400 transition-colors shrink-0 ml-3" />
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}