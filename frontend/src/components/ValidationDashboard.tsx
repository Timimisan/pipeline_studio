import type { ValidationScores, AttemptCounts, PipelineStage } from '../types';
import { BarChart3, AlertTriangle, CheckCircle2, TrendingUp, Activity } from 'lucide-react';

interface Props {
  scores?: ValidationScores;
  attempts?: AttemptCounts;
}

const stageConfig: { key: PipelineStage; label: string; color: string; gradient: string }[] = [
  { key: 'reasoning_state', label: 'Reasoning', color: 'bg-purple-500', gradient: 'from-purple-500 to-fuchsia-500' },
  { key: 'subject_line', label: 'Subject', color: 'bg-blue-500', gradient: 'from-blue-500 to-cyan-500' },
  { key: 'hook', label: 'Hook', color: 'bg-indigo-500', gradient: 'from-indigo-500 to-violet-500' },
  { key: 'tension', label: 'Tension', color: 'bg-amber-500', gradient: 'from-amber-500 to-orange-500' },
  { key: 'transition_question', label: 'Transition', color: 'bg-pink-500', gradient: 'from-pink-500 to-rose-500' },
  { key: 'authority', label: 'Authority', color: 'bg-emerald-500', gradient: 'from-emerald-500 to-teal-500' },
  { key: 'cta', label: 'CTA', color: 'bg-cyan-500', gradient: 'from-cyan-500 to-sky-500' },
];

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  const percentage = Math.round((value || 0) * 100);
  let statusColor = 'text-emerald-400';
  let StatusIcon = CheckCircle2;
  let barColor = 'bg-emerald-500';

  if (percentage < 60) {
    statusColor = 'text-red-400';
    StatusIcon = AlertTriangle;
    barColor = 'bg-red-500';
  } else if (percentage < 75) {
    statusColor = 'text-amber-400';
    StatusIcon = AlertTriangle;
    barColor = 'bg-amber-500';
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center text-xs">
        <span className="font-medium text-slate-400">{label}</span>
        <span className={`font-semibold flex items-center gap-1 ${statusColor}`}>
          <StatusIcon className="w-3 h-3" />
          {percentage}%
        </span>
      </div>
      <div className="progress-track">
        <div
          className={`progress-fill ${barColor}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export default function ValidationDashboard({ scores = {}, attempts = {} }: Props) {
  const totalAttempts = Object.values(attempts).reduce((sum, val) => sum + (val || 0), 0);
  const avgScore = Object.values(scores).reduce((sum, stageScores) => {
    const latest = stageScores?.[stageScores.length - 1] || {};
    const vals = Object.values(latest).filter(v => typeof v === 'number') as number[];
    return sum + (vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0);
  }, 0) / (Object.keys(scores).length || 1);

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Validation Scores</h3>
            <p className="text-xs text-slate-500">Pipeline stage performance metrics</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Avg Score</p>
            <p className="text-lg font-bold text-white">{Math.round(avgScore * 100)}%</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Total Attempts</p>
            <p className="text-lg font-bold text-white">{totalAttempts}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {stageConfig.map((stage) => {
          const stageScores = scores?.[stage.key] || [];
          const attemptCount = attempts?.[stage.key] || 0;
          const latestScores = stageScores?.[stageScores.length - 1] || {};
          const hasScores = Object.keys(latestScores).length > 0;

          return (
            <div key={stage.key} className="p-5 bg-white/[0.02] rounded-xl border border-white/[0.04] hover:border-white/[0.08] transition-all">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${stage.gradient}`} />
                  <h4 className="font-semibold text-white text-sm">{stage.label}</h4>
                </div>
                <span className="text-[10px] font-medium text-slate-600 bg-slate-800/50 px-2 py-1 rounded">
                  {attemptCount} attempt{attemptCount !== 1 ? 's' : ''}
                </span>
              </div>

              <div className="space-y-3">
                {hasScores ? (
                  Object.entries(latestScores).map(([metric, value]) => (
                    <ScoreBar
                      key={metric}
                      label={metric.replace(/_/g, ' ').replace(/\w/g, l => l.toUpperCase())}
                      value={value as number}
                      color={stage.color}
                    />
                  ))
                ) : (
                  <div className="flex items-center gap-2 text-xs text-slate-600 py-2">
                    <Activity className="w-3 h-3" />
                    No detailed scores available
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}