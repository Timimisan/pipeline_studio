import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import ContextForm from '../components/ContextForm';
import PipelineRunner from '../components/PipelineRunner';
import { FileText, Plus, ChevronDown, ChevronUp, Clock, ArrowLeft, Building2, UserCog, ListChecks, Zap } from 'lucide-react';

export default function ProblemDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { state } = useApp();
  const [showContextForm, setShowContextForm] = useState(false);

  const problem = state.problems.find(p => String(p?.problem_id) === id);
  const contexts = state.contexts.filter(c => String(c?.problem_id ?? c?.problemId ?? '') === String(id));

  if (!state.hydrated) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="text-center py-20">
        <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
          <FileText className="w-8 h-8 text-slate-600" />
        </div>
        <h2 className="text-xl font-semibold text-white">Problem not found</h2>
        <p className="text-slate-500 mt-2 text-sm">URL ID: <code className="bg-slate-800 px-2 py-0.5 rounded text-slate-400">{id}</code></p>
        <p className="text-slate-600 mt-1 text-sm">
          Stored IDs: {state.problems.map(p => String(p?.problem_id)).join(', ') || 'none'}
        </p>
        <Link to="/" className="mt-6 inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 text-sm font-medium transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const snapshot = problem.snapshot || {};
  const fullData = problem.fullData || {};

  const detailFields = [
    { label: 'Core Problem', value: fullData.core_problem },
    { label: 'Causal Mechanism', value: fullData.causal_mechanism },
    { label: 'Failure Mode A', value: fullData.failure_mode_A },
    { label: 'Failure Mode B', value: fullData.failure_mode_B },
    { label: 'Contradiction', value: fullData.contradiction, highlight: true },
    { label: 'Solution Actor', value: fullData.solution_actor },
    { label: 'Solution Mechanism', value: fullData.solution_mechanism },
  ];

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Back Button & Header */}
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-slate-500 hover:text-white transition-colors mb-4 text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">{snapshot.problem_name || 'Untitled'}</h1>
            <p className="text-slate-500 mt-1">{snapshot.system || ''}</p>
            <div className="flex items-center gap-2 mt-3 text-xs text-slate-600">
              <Clock className="w-3 h-3" />
              {problem.createdAt ? new Date(problem.createdAt).toLocaleDateString() : '—'}
            </div>
          </div>
          <div className="badge badge-info">
            <Zap className="w-3 h-3" />
            Active
          </div>
        </div>
      </div>

      {/* Problem Definition Card */}
      <div className="glass-card">
        <div className="px-6 py-4 border-b border-white/[0.06] flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <h3 className="font-semibold text-white">Problem Definition</h3>
        </div>
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          {detailFields.map((field) => (
            <div key={field.label} className={field.highlight ? 'md:col-span-2' : ''}>
              <label className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-2 block">
                {field.label}
              </label>
              <p className={`text-sm leading-relaxed ${field.highlight ? 'text-indigo-300 font-medium' : 'text-slate-400'}`}>
                {field.value || '—'}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Contexts Section */}
      <div className="glass-card overflow-hidden">
        <button
          onClick={() => setShowContextForm(!showContextForm)}
          className="w-full px-6 py-4 border-b border-white/[0.06] flex items-center justify-between hover:bg-white/[0.02] transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
              <Building2 className="w-4 h-4 text-white" />
            </div>
            <div className="text-left">
              <h3 className="font-semibold text-white">Contexts</h3>
              <p className="text-xs text-slate-500 mt-0.5">{contexts.length} defined</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {!showContextForm && (
              <span className="text-xs text-slate-600 flex items-center gap-1">
                <Plus className="w-3 h-3" />
                Add
              </span>
            )}
            {showContextForm ? (
              <ChevronUp className="w-4 h-4 text-slate-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-500" />
            )}
          </div>
        </button>

        {showContextForm && (
          <div className="p-6 border-b border-white/[0.06] bg-gradient-to-b from-indigo-500/[0.03] to-transparent">
            <ContextForm
              problemId={String(problem.problem_id ?? '')}
              onSuccess={() => setShowContextForm(false)}
            />
          </div>
        )}

        <div className="divide-y divide-white/[0.04]">
          {contexts.length === 0 ? (
            <div className="p-8 text-center">
              <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center mx-auto mb-3">
                <ListChecks className="w-6 h-6 text-slate-600" />
              </div>
              <p className="text-sm text-slate-500">No contexts yet</p>
              <p className="text-xs text-slate-600 mt-1">Add one to run the pipeline</p>
            </div>
          ) : (
            contexts.map(c => (
              <div
                key={String(c?.context_id ?? Math.random())}
                className="p-5 flex items-center justify-between hover:bg-white/[0.02] transition-colors group"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center">
                    <UserCog className="w-5 h-5 text-slate-400" />
                  </div>
                  <div>
                    <p className="font-medium text-white text-sm">
                      {c?.snapshot?.industry || '—'} • {c?.snapshot?.company_size || '—'}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Actor: <span className="text-slate-400">{c?.snapshot?.decision_actor || '—'}</span>
                      <span className="mx-2 text-slate-700">|</span>
                      Constraints: <span className="text-slate-400">{c?.snapshot?.constraints?.length ?? 0}</span>
                    </p>
                  </div>
                </div>
                <span className="text-[10px] font-mono text-slate-700 bg-slate-800/50 px-2 py-1 rounded">
                  ID: {c?.context_id}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Pipeline Runner */}
      {contexts.length > 0 && (
        <PipelineRunner problemId={String(problem.problem_id ?? '')} contexts={contexts} />
      )}
    </div>
  );
}