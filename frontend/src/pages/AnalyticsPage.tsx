import { useEffect, useState } from 'react';
import { getAnalytics, getDailyAnalytics } from '../api/client';
import { useApp } from '../context/AppContext';
import type { AnalyticsData, DailyAnalytics, EmailAnalytics } from '../types';
import {
  Activity, TrendingUp, AlertTriangle, CheckCircle,
  Clock, DollarSign, BarChart3, Zap, RefreshCw, Mail,
  ChevronDown, ChevronUp
} from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: React.ElementType;
  gradient: string;
  glow: string;
}

function MetricCard({ label, value, icon: Icon, gradient, glow }: MetricCardProps) {
  return (
    <div className="metric-card group">
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-2">{label}</p>
          <p className="text-2xl font-bold text-white tracking-tight">{value}</p>
        </div>
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-lg ${glow}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </div>
  );
}

interface SimpleBarProps {
  label: string;
  value: number;
  max: number;
  gradient: string;
  suffix?: string;
}

function SimpleBar({ label, value, max, gradient, suffix = '' }: SimpleBarProps) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs">
        <span className="font-medium text-slate-400">{label.replace(/_/g, ' ')}</span>
        <span className="font-semibold text-white">{value}{suffix}</span>
      </div>
      <div className="progress-track">
        <div className={`progress-fill bg-gradient-to-r ${gradient}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  );
}

function SimplePie({ data }: { data: Array<{ label: string; value: number; color: string }> }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  let cumulative = 0;

  return (
    <div className="flex items-center gap-8">
      <div className="relative w-36 h-36">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          {data.map((slice, i) => {
            const pct = total > 0 ? (slice.value / total) * 100 : 0;
            const start = cumulative;
            cumulative += pct;
            const end = cumulative;

            const x1 = 50 + 40 * Math.cos((start * 3.6) * Math.PI / 180);
            const y1 = 50 + 40 * Math.sin((start * 3.6) * Math.PI / 180);
            const x2 = 50 + 40 * Math.cos((end * 3.6) * Math.PI / 180);
            const y2 = 50 + 40 * Math.sin((end * 3.6) * Math.PI / 180);
            const largeArc = pct > 50 ? 1 : 0;

            if (pct === 0) return null;

            return (
              <path
                key={i}
                d={`M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArc} 1 ${x2} ${y2} Z`}
                fill={slice.color}
                stroke="#0a0a0f"
                strokeWidth="2"
              />
            );
          })}
          <circle cx="50" cy="50" r="22" fill="#0a0a0f" />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-bold text-white">{total}</span>
        </div>
      </div>
      <div className="space-y-3 flex-1">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-3 text-sm">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }} />
            <span className="text-slate-400">{d.label.replace(/_/g, ' ')}</span>
            <span className="font-semibold text-white ml-auto">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const GRADIENTS = [
  'from-purple-500 to-fuchsia-500',
  'from-blue-500 to-cyan-500',
  'from-amber-500 to-orange-500',
  'from-red-500 to-pink-500',
  'from-emerald-500 to-teal-500',
  'from-pink-500 to-rose-500',
];

const HEX_COLORS = ['#8b5cf6', '#3b82f6', '#f59e0b', '#ef4444', '#10b981', '#ec4899'];

// Empty state when no data from backend
const EMPTY_ANALYTICS: AnalyticsData = {
  average_retries: 0,
  top_failure_modes: [],
  validator_disagreement_rate: 0,
  repair_success_rate: 0,
  average_latency_ms: 0,
  average_cost: 0,
  total_emails_generated: 0,
};

const EMPTY_DAILY: DailyAnalytics[] = [
  { day: 'Mon', date: '', latency: 0, cost: 0, retries: 0, emails: 0 },
  { day: 'Tue', date: '', latency: 0, cost: 0, retries: 0, emails: 0 },
  { day: 'Wed', date: '', latency: 0, cost: 0, retries: 0, emails: 0 },
  { day: 'Thu', date: '', latency: 0, cost: 0, retries: 0, emails: 0 },
  { day: 'Fri', date: '', latency: 0, cost: 0, retries: 0, emails: 0 },
  { day: 'Sat', date: '', latency: 0, cost: 0, retries: 0, emails: 0 },
  { day: 'Sun', date: '', latency: 0, cost: 0, retries: 0, emails: 0 },
];

export default function AnalyticsPage() {
  const { state, syncWithBackend } = useApp();

  // Main analytics
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Daily trends (from backend)
  const [dailyData, setDailyData] = useState<DailyAnalytics[]>(EMPTY_DAILY);
  const [dailyLoading, setDailyLoading] = useState(true);
  const [dailyError, setDailyError] = useState('');

  // Per-context email analytics
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null);

  // Fetch main analytics
  useEffect(() => {
    getAnalytics()
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        setError(`Backend unavailable: ${err.message}`);
        setData(EMPTY_ANALYTICS);
        setLoading(false);
      });
  }, []);

  // Fetch daily trends
  useEffect(() => {
    getDailyAnalytics()
      .then(d => {
        setDailyData(d.length > 0 ? d : EMPTY_DAILY);
        setDailyLoading(false);
      })
      .catch(err => {
        setDailyError(`Daily trends unavailable: ${err.message}`);
        setDailyData(EMPTY_DAILY);
        setDailyLoading(false);
      });
  }, []);

  if (loading || dailyLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const analytics = data || EMPTY_ANALYTICS;
  const trendData = dailyData;

  const metricCards = [
    { label: 'Avg Retries', value: analytics.average_retries.toFixed(2), icon: Activity, gradient: 'from-blue-500 to-cyan-500', glow: 'shadow-blue-500/20' },
    { label: 'Repair Success', value: `${(analytics.repair_success_rate * 100).toFixed(0)}%`, icon: CheckCircle, gradient: 'from-emerald-500 to-teal-500', glow: 'shadow-emerald-500/20' },
    { label: 'Validator Disagreement', value: `${(analytics.validator_disagreement_rate * 100).toFixed(1)}%`, icon: AlertTriangle, gradient: 'from-amber-500 to-orange-500', glow: 'shadow-amber-500/20' },
    { label: 'Avg Latency', value: `${(analytics.average_latency_ms / 1000).toFixed(1)}s`, icon: Clock, gradient: 'from-purple-500 to-fuchsia-500', glow: 'shadow-purple-500/20' },
    { label: 'Avg Cost', value: `$${analytics.average_cost.toFixed(3)}`, icon: DollarSign, gradient: 'from-green-500 to-emerald-500', glow: 'shadow-green-500/20' },
    { label: 'Total Emails', value: analytics.total_emails_generated, icon: TrendingUp, gradient: 'from-indigo-500 to-violet-500', glow: 'shadow-indigo-500/20' },
  ];

  const maxFailures = Math.max(...analytics.top_failure_modes.map(f => f.count), 1);
  const maxLatency = Math.max(...trendData.map(d => d.latency), 1);
  const maxCost = Math.max(...trendData.map(d => d.cost), 0.001); // avoid div by zero
  const maxEmails = Math.max(...trendData.map(d => d.emails), 1);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="page-title">Pipeline Analytics</h1>
          <p className="page-subtitle">Performance, cost, and quality metrics — from backend</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={syncWithBackend}
            className="btn-premium btn-premium-secondary text-sm"
          >
            <RefreshCw className="w-4 h-4" />
            Sync Data
          </button>
        </div>
      </div>

      {(error || dailyError) && (
        <div className="alert-premium alert-error">
          <AlertTriangle className="w-4 h-4" />
          {error || dailyError}
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {metricCards.map((card) => (
          <MetricCard key={card.label} {...card} />
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Failure Modes Bar Chart */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-pink-500 flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Top Failure Modes</h3>
              <p className="text-xs text-slate-500">
                {analytics.top_failure_modes.length > 0 ? 'From backend' : 'No failure data yet'}
              </p>
            </div>
          </div>
          <div className="space-y-4">
            {analytics.top_failure_modes.length > 0 ? (
              analytics.top_failure_modes.map((fm, i) => (
                <SimpleBar
                  key={fm.class}
                  label={fm.class}
                  value={fm.count}
                  max={maxFailures}
                  gradient={GRADIENTS[i % GRADIENTS.length]}
                  suffix={` (${fm.percentage}%)`}
                />
              ))
            ) : (
              <div className="text-center py-8 text-slate-600 text-sm">
                <BarChart3 className="w-8 h-8 mx-auto mb-2 text-slate-700" />
                No failure data recorded yet
              </div>
            )}
          </div>
        </div>

        {/* Failure Distribution Pie */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-fuchsia-500 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Failure Distribution</h3>
              <p className="text-xs text-slate-500">
                {analytics.top_failure_modes.length > 0 ? 'From backend' : 'No data'}
              </p>
            </div>
          </div>
          {analytics.top_failure_modes.length > 0 ? (
            <SimplePie
              data={analytics.top_failure_modes.map((fm, i) => ({
                label: fm.class,
                value: fm.count,
                color: HEX_COLORS[i % HEX_COLORS.length],
              }))}
            />
          ) : (
            <div className="text-center py-8 text-slate-600 text-sm">
              <Zap className="w-8 h-8 mx-auto mb-2 text-slate-700" />
              No failure distribution data
            </div>
          )}
        </div>

        {/* Latency Trends — REAL DATA FROM BACKEND */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Clock className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Latency Trends</h3>
              <p className="text-xs text-slate-500">
                {dailyError ? 'Backend unavailable' : 'Last 7 days from backend'}
              </p>
            </div>
          </div>
          <div className="space-y-3">
            {trendData.map(d => (
              <div key={d.day} className="flex items-center gap-3">
                <span className="text-xs font-medium text-slate-500 w-8">{d.day}</span>
                <div className="flex-1 progress-track">
                  <div
                    className="progress-fill bg-gradient-to-r from-blue-500 to-cyan-500"
                    style={{ width: `${(d.latency / maxLatency) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-slate-400 w-12 text-right">
                  {d.latency > 0 ? `${d.latency}s` : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Cost Trends — REAL DATA FROM BACKEND */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
              <DollarSign className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">Cost Trends</h3>
              <p className="text-xs text-slate-500">
                {dailyError ? 'Backend unavailable' : 'Last 7 days from backend'}
              </p>
            </div>
          </div>
          <div className="space-y-3">
            {trendData.map(d => (
              <div key={d.day} className="flex items-center gap-3">
                <span className="text-xs font-medium text-slate-500 w-8">{d.day}</span>
                <div className="flex-1 progress-track">
                  <div
                    className="progress-fill bg-gradient-to-r from-emerald-500 to-teal-500"
                    style={{ width: `${(d.cost / maxCost) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-slate-400 w-16 text-right">
                  {d.cost > 0 ? `$${d.cost.toFixed(3)}` : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Repair Success */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
            <RefreshCw className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Repair Success Analysis</h3>
            <p className="text-xs text-slate-500">Pipeline recovery metrics from backend</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-emerald-500/5 rounded-xl border border-emerald-500/10 p-6 text-center">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-3">
              <CheckCircle className="w-6 h-6 text-emerald-400" />
            </div>
            <p className="text-3xl font-bold text-white">{(analytics.repair_success_rate * 100).toFixed(0)}%</p>
            <p className="text-sm text-emerald-400 mt-1 font-medium">Repair Success Rate</p>
            <p className="text-xs text-slate-600 mt-2">Failed validation → fixed on retry</p>
          </div>
          <div className="bg-amber-500/5 rounded-xl border border-amber-500/10 p-6 text-center">
            <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center mx-auto mb-3">
              <RefreshCw className="w-6 h-6 text-amber-400" />
            </div>
            <p className="text-3xl font-bold text-white">{analytics.average_retries.toFixed(1)}</p>
            <p className="text-sm text-amber-400 mt-1 font-medium">Average Retries</p>
            <p className="text-xs text-slate-600 mt-2">Per stage before success</p>
          </div>
          <div className="bg-red-500/5 rounded-xl border border-red-500/10 p-6 text-center">
            <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center mx-auto mb-3">
              <AlertTriangle className="w-6 h-6 text-red-400" />
            </div>
            <p className="text-3xl font-bold text-white">{(analytics.validator_disagreement_rate * 100).toFixed(1)}%</p>
            <p className="text-sm text-red-400 mt-1 font-medium">Validator Disagreement</p>
            <p className="text-xs text-slate-600 mt-2">LLM validators conflict</p>
          </div>
        </div>
      </div>

      {/* Weekly Volume — REAL DATA FROM BACKEND */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Weekly Email Volume</h3>
            <p className="text-xs text-slate-500">
              {dailyError ? 'Backend unavailable' : 'Emails generated per day from backend'}
            </p>
          </div>
        </div>
        <div className="flex items-end gap-3 h-40 px-4">
          {trendData.map(d => {
            const pct = (d.emails / maxEmails) * 100;
            return (
              <div key={d.day} className="flex-1 flex flex-col items-center gap-2">
                <span className="text-xs font-semibold text-white">{d.emails > 0 ? d.emails : '—'}</span>
                <div
                  className="w-full bg-gradient-to-t from-blue-600 to-indigo-500 rounded-t-lg transition-all duration-500 hover:from-blue-500 hover:to-indigo-400 min-h-[4px]"
                  style={{ height: `${d.emails > 0 ? pct : 4}%` }}
                />
                <span className="text-xs text-slate-500">{d.day}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}