import { useEffect, useRef } from 'react';
import type { PipelineTrace, StageTrace } from '../types';
import {
  Brain, Type, Anchor, Zap, HelpCircle, Shield, MessageSquare, Mail,
  CheckCircle, XCircle, Loader2, AlertTriangle, RefreshCw, Clock, DollarSign, Hash
} from 'lucide-react';

interface Props {
  trace: PipelineTrace | null;
  isRunning: boolean;
}

const stageConfig: Record<string, { label: string; icon: any; gradient: string; glow: string }> = {
  reasoning_state: { label: 'Reasoning', icon: Brain, gradient: 'from-purple-500 to-fuchsia-500', glow: 'shadow-purple-500/20' },
  subject_line: { label: 'Subject Line', icon: Type, gradient: 'from-blue-500 to-cyan-500', glow: 'shadow-blue-500/20' },
  hook: { label: 'Hook', icon: Anchor, gradient: 'from-indigo-500 to-violet-500', glow: 'shadow-indigo-500/20' },
  tension: { label: 'Tension', icon: Zap, gradient: 'from-amber-500 to-orange-500', glow: 'shadow-amber-500/20' },
  transition_question: { label: 'Transition', icon: HelpCircle, gradient: 'from-pink-500 to-rose-500', glow: 'shadow-pink-500/20' },
  authority: { label: 'Authority', icon: Shield, gradient: 'from-emerald-500 to-teal-500', glow: 'shadow-emerald-500/20' },
  cta: { label: 'CTA', icon: MessageSquare, gradient: 'from-cyan-500 to-sky-500', glow: 'shadow-cyan-500/20' },
  final_assembly: { label: 'Assembly', icon: Mail, gradient: 'from-slate-500 to-slate-400', glow: 'shadow-slate-500/20' },
};

function StageCard({ stage, isLatest }: { stage: StageTrace; isLatest: boolean }) {
  const config = stageConfig[stage.stage] || { label: stage.stage, icon: Mail, gradient: 'from-slate-500 to-slate-400', glow: '' };
  const Icon = config.icon;

  const statusConfig = {
    started: { icon: <Loader2 className="w-4 h-4 animate-spin text-blue-400" />, bg: 'bg-blue-500/5', border: 'border-blue-500/20', text: 'text-blue-400' },
    success: { icon: <CheckCircle className="w-4 h-4 text-emerald-400" />, bg: 'bg-emerald-500/5', border: 'border-emerald-500/20', text: 'text-emerald-400' },
    failed: { icon: <XCircle className="w-4 h-4 text-red-400" />, bg: 'bg-red-500/5', border: 'border-red-500/20', text: 'text-red-400' },
    repairing: { icon: <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />, bg: 'bg-amber-500/5', border: 'border-amber-500/20', text: 'text-amber-400' },
    complete: { icon: <CheckCircle className="w-4 h-4 text-emerald-400" />, bg: 'bg-emerald-500/5', border: 'border-emerald-500/20', text: 'text-emerald-400' },
  };

  const status = statusConfig[stage.status] || statusConfig.started;

  return (
    <div className={`relative p-5 rounded-xl border transition-all duration-500 ${status.bg} ${status.border} ${isLatest ? 'ring-1 ring-indigo-500/30 scale-[1.01]' : ''}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${config.gradient} flex items-center justify-center shadow-lg ${config.glow}`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h4 className="font-semibold text-sm text-white">{config.label}</h4>
            <div className="flex items-center gap-2 mt-1">
              {status.icon}
              <span className={`text-xs font-medium capitalize ${status.text}`}>{stage.status}</span>
              {isLatest && stage.status === 'started' && (
                <span className="text-xs text-indigo-400 animate-pulse">Generating...</span>
              )}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1 text-xs font-mono text-slate-500">
            <Clock className="w-3 h-3" />
            {stage.latency_ms.toFixed(0)}ms
          </div>
          {stage.cost > 0 && (
            <div className="flex items-center gap-1 text-xs font-mono text-emerald-400 mt-1">
              <DollarSign className="w-3 h-3" />
              {stage.cost.toFixed(4)}
            </div>
          )}
        </div>
      </div>

      {(stage.tokens_in > 0 || stage.tokens_out > 0) && (
        <div className="mt-4 pt-4 border-t border-white/[0.06] grid grid-cols-3 gap-3 text-xs">
          <div className="bg-white/[0.02] rounded-lg p-2">
            <span className="text-slate-600 text-[10px] uppercase tracking-wider">Tokens In</span>
            <p className="font-mono font-semibold text-slate-300 mt-1">{stage.tokens_in}</p>
          </div>
          <div className="bg-white/[0.02] rounded-lg p-2">
            <span className="text-slate-600 text-[10px] uppercase tracking-wider">Tokens Out</span>
            <p className="font-mono font-semibold text-slate-300 mt-1">{stage.tokens_out}</p>
          </div>
          <div className="bg-white/[0.02] rounded-lg p-2">
            <span className="text-slate-600 text-[10px] uppercase tracking-wider">Cost</span>
            <p className="font-mono font-semibold text-emerald-400 mt-1">${stage.cost.toFixed(4)}</p>
          </div>
        </div>
      )}

      {stage.retry_count > 0 && (
        <div className="mt-3 flex items-center gap-2 text-xs bg-amber-500/5 rounded-lg p-2 border border-amber-500/10">
          <RefreshCw className="w-3 h-3 text-amber-400" />
          <span className="text-amber-400 font-medium">{stage.retry_count} retries</span>
        </div>
      )}

      {stage.failure_reason && stage.status !== 'success' && (
        <div className="mt-3 p-3 bg-red-500/5 rounded-lg border border-red-500/10">
          <div className="flex items-center gap-2 text-red-400 font-semibold text-xs">
            <AlertTriangle className="w-3 h-3" />
            {stage.failure_class || 'unknown'}
          </div>
          <p className="text-red-300/70 text-xs mt-1 leading-relaxed">{stage.failure_reason}</p>
        </div>
      )}

      {stage.attempts_history.length > 1 && (
        <div className="mt-4 space-y-2">
          <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Attempt History</p>
          {stage.attempts_history.map((attempt, i) => (
            <div key={i} className="flex items-center gap-3 text-xs bg-white/[0.02] rounded-lg p-2">
              <div className={`w-2 h-2 rounded-full ${attempt.valid ? 'bg-emerald-400' : 'bg-red-400'}`} />
              <span className="text-slate-400 font-medium">Attempt {attempt.attempt}</span>
              {attempt.scores && (
                <span className="text-slate-600 font-mono text-[10px]">
                  {Object.entries(attempt.scores).map(([k, v]) => `${k}: ${(v as number).toFixed(2)}`).join(', ')}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function LivePipelineTracker({ trace, isRunning }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const latestStage = trace?.stages[trace.stages.length - 1];

  useEffect(() => {
    if (scrollRef.current && latestStage) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [trace?.stages.length]);

  if (!isRunning && !trace) return null;

  return (
    <div className="glass-card overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 px-6 py-4 flex items-center justify-between border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isRunning ? 'bg-blue-500/20' : 'bg-emerald-500/20'}`}>
            <Loader2 className={`w-5 h-5 ${isRunning ? 'animate-spin text-blue-400' : 'text-emerald-400'}`} />
          </div>
          <div>
            <h3 className="font-semibold text-white">Live Pipeline Tracker</h3>
            {trace && (
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                <span className="text-slate-600">Request:</span> {trace.request_id.slice(0, 8)}...
                <span className="mx-2 text-slate-700">|</span>
                <span className="text-slate-600">Latency:</span> {trace.total_latency_ms.toFixed(0)}ms
                <span className="mx-2 text-slate-700">|</span>
                <span className="text-slate-600">Cost:</span> ${trace.total_cost.toFixed(4)}
              </p>
            )}
          </div>
        </div>
        {trace?.final_status === 'complete' && (
          <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 text-xs rounded-full font-medium border border-emerald-500/20">
            Complete
          </span>
        )}
      </div>

      {/* Stages */}
      <div ref={scrollRef} className="p-6 space-y-4 max-h-[600px] overflow-y-auto">
        {trace?.stages.map((stage, index) => (
          <StageCard
            key={`${stage.stage}-${index}`}
            stage={stage}
            isLatest={index === trace.stages.length - 1}
          />
        ))}

        {isRunning && trace?.final_status !== 'complete' && (
          <div className="flex items-center gap-3 text-sm text-slate-500 py-4">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
            <span className="animate-pulse">Waiting for next stage...</span>
          </div>
        )}
      </div>

      {/* Footer Stats */}
      {trace && trace.stages.length > 0 && (
        <div className="bg-white/[0.02] px-6 py-4 border-t border-white/[0.06] grid grid-cols-4 gap-4 text-sm">
          <div className="bg-white/[0.02] rounded-lg p-3">
            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Total Stages</p>
            <p className="font-semibold text-white mt-1 text-lg">{trace.stages.length}</p>
          </div>
          <div className="bg-white/[0.02] rounded-lg p-3">
            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Total Retries</p>
            <p className="font-semibold text-amber-400 mt-1 text-lg">
              {trace.stages.reduce((sum, s) => sum + s.retry_count, 0)}
            </p>
          </div>
          <div className="bg-white/[0.02] rounded-lg p-3">
            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Total Tokens</p>
            <p className="font-semibold text-white mt-1 text-lg">
              {trace.total_tokens_in + trace.total_tokens_out}
            </p>
          </div>
          <div className="bg-white/[0.02] rounded-lg p-3">
            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Total Cost</p>
            <p className="font-semibold text-emerald-400 mt-1 text-lg">${trace.total_cost.toFixed(4)}</p>
          </div>
        </div>
      )}
    </div>
  );
}