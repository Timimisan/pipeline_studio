import { useState, useEffect } from 'react';
import { runPipelineStream } from '../api/client';
import { useApp } from '../context/AppContext';
import type { Context, PipelineResult, PipelineTrace } from '../types';
import LivePipelineTracker from './LivePipelineTracker';
import EmailViewer from './EmailViewer';
import ValidationDashboard from './ValidationDashboard';
import { Play, AlertCircle, CheckCircle, Zap, Building2 } from 'lucide-react';

interface Props {
  problemId: string;
  contexts: Context[];
}

export default function PipelineRunner({ problemId, contexts }: Props) {
  const [selectedContextId, setSelectedContextId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [liveTrace, setLiveTrace] = useState<PipelineTrace | null>(null);
  const { state, dispatch } = useApp();

  // Debug: log when contexts change
  useEffect(() => {
    console.log('[PipelineRunner] contexts prop:', contexts.length, 'items');
    contexts.forEach((c, i) => {
      console.log(`  [${i}] id=${c?.id}, context_id=${c?.context_id}, industry=${c?.snapshot?.industry ?? c?.industry}`);
    });
  }, [contexts]);

  const handleRun = async () => {
    if (!selectedContextId || selectedContextId === '') {
      setError('Please select a context first');
      return;
    }

    console.log('[PipelineRunner] Starting with:', { problemId, context_id: selectedContextId });

    setLoading(true);
    setError('');
    setResult(null);
    setLiveTrace(null);

    try {
      const abort = runPipelineStream(
        {
          problem_id: problemId,
          context_id: selectedContextId,
        },
        (trace) => {
          console.log('[PipelineRunner] Trace update:', trace.stages?.length, 'stages');
          setLiveTrace(trace);
        },
        (data) => {
          console.log('[PipelineRunner] Complete:', data.final_email_id);
          setResult(data);
          setLoading(false);

          const problem = state.problems.find(p =>
            String(p?.problem_id ?? p?.id) === String(problemId)
          );
          const context = state.contexts.find(c =>
            String(c?.context_id ?? c?.id) === String(selectedContextId)
          );

          dispatch({
            type: 'ADD_EMAIL',
            payload: {
              ...data,
              id: `${data.final_email_id}-${Date.now()}`,
              problemName: problem?.snapshot?.problem_name ?? problem?.problem_name ?? 'Unknown',
              contextName: `${context?.snapshot?.industry ?? context?.industry ?? ''} • ${context?.snapshot?.company_size ?? context?.company_size ?? ''}`,
              createdAt: new Date().toISOString(),
            }
          });
        },
        (err) => {
          console.error('[PipelineRunner] Error:', err);
          setError(err || 'Stream error');
          setLoading(false);
        }
      );

      // Store abort function for cleanup
      return () => abort();
    } catch (err: any) {
      console.error('[PipelineRunner] Exception:', err);
      setError(err?.message || 'Failed to start pipeline');
      setLoading(false);
    }
  };

  // Find selected context for preview
  const selectedContext = contexts.find(c => {
    const cid = String(c?.context_id ?? c?.id ?? '');
    return cid === selectedContextId;
  });

  // Determine if we can run
  const hasValidContext = selectedContextId !== '' && selectedContextId !== '0';
  const canRun = hasValidContext && !loading && !!problemId;

  // Debug render
  console.log('[PipelineRunner] Render:', {
    selectedContextId,
    hasValidContext,
    canRun,
    loading,
    contextsCount: contexts.length
  });

  if (!contexts || contexts.length === 0) {
    return (
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <h3 className="font-semibold text-white">Run Pipeline</h3>
        </div>
        <p className="text-sm text-slate-500">No contexts available. Add a context first.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Run Panel */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Run Pipeline</h3>
            <p className="text-xs text-slate-500">Execute the constrained persuasion pipeline</p>
          </div>
        </div>

        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="input-label-premium mb-2 block">Select Context</label>
            <div className="relative">
              <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
              <select
                className="input-premium select-premium pl-10"
                value={selectedContextId}
                onChange={e => {
                  const val = e.target.value;
                  console.log('[PipelineRunner] Select changed to:', val);
                  setSelectedContextId(val);
                  setError(''); // Clear error on selection
                }}
              >
                <option value="">Choose a context...</option>
                {contexts.map((c, idx) => {
                  const cid = c?.context_id ?? c?.id ?? '';
                  if (!cid) {
                    console.warn('[PipelineRunner] Context missing ID:', c);
                    return null;
                  }
                  const industry = c?.snapshot?.industry ?? c?.industry ?? '—';
                  const size = c?.snapshot?.company_size ?? c?.company_size ?? '—';
                  const actor = c?.snapshot?.decision_actor ?? c?.decision_actor ?? '—';
                  return (
                    <option key={`ctx-${cid}-${idx}`} value={String(cid)}>
                      {industry} • {size} • {actor}
                    </option>
                  );
                })}
              </select>
            </div>
          </div>
          <button
            onClick={handleRun}
            disabled={!canRun}
            className="btn-premium btn-premium-primary h-[46px] px-6"
            style={{
              opacity: canRun ? 1 : 0.5,
              cursor: canRun ? 'pointer' : 'not-allowed'
            }}
          >
            {loading ? (
              <>
                <div className="spinner-premium" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Pipeline
              </>
            )}
          </button>
        </div>

        {/* Debug info */}
        <div className="mt-3 text-[10px] font-mono text-slate-700">
          Debug: selected={selectedContextId || 'none'} | canRun={canRun ? 'yes' : 'no'} | contexts={contexts.length}
        </div>

        {selectedContext && (
          <div className="mt-5 p-4 bg-white/[0.02] rounded-xl border border-white/[0.04] text-sm">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-1">Actor</p>
                <p className="text-slate-300">{selectedContext.snapshot?.decision_actor ?? selectedContext.decision_actor ?? '—'}</p>
              </div>
              <div>
                <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-1">Constraints</p>
                <p className="text-slate-300">{(selectedContext.snapshot?.constraints ?? selectedContext.constraints ?? []).join(', ') || 'None'}</p>
              </div>
              {selectedContext.snapshot?.extra && (
                <div>
                  <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-1">Extra</p>
                  <p className="text-slate-300">{selectedContext.snapshot.extra}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 alert-premium alert-error">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}
      </div>

      {/* Live Tracker */}
      <LivePipelineTracker trace={liveTrace} isRunning={loading} />

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-fade-in-up">
          <div className="flex items-center gap-3 p-4 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            </div>
            <span className="font-semibold text-emerald-400">Pipeline completed successfully</span>
          </div>

          <EmailViewer
            subject={result.subject_line || ''}
            body={result.email || ''}
            emailId={result.final_email_id}
          />

          <ValidationDashboard
            scores={result.validation_scores || {}}
            attempts={result.attempts || {}}
          />
        </div>
      )}
    </div>
  );
}