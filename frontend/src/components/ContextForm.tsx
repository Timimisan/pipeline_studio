import { useState } from 'react';
import { createContext } from '../api/client';
import { useApp } from '../context/AppContext';
import type { CreateContextRequest } from '../types';
import { X, Plus, Save, AlertCircle, Building2, Users, UserCog, FileText, ArrowLeft } from 'lucide-react';

interface Props {
  problemId: string;
  onSuccess?: () => void;
}

export default function ContextForm({ problemId, onSuccess }: Props) {
  const [form, setForm] = useState<CreateContextRequest>({
    problem_id: problemId,
    industry: '',
    company_size: '',
    decision_actor: '',
    extra: '',
    constraints: [],
  });
  const [constraintInput, setConstraintInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { dispatch } = useApp();

  const addConstraint = () => {
    if (!constraintInput.trim()) return;
    setForm(prev => ({ ...prev, constraints: [...prev.constraints, constraintInput.trim()] }));
    setConstraintInput('');
  };

  const removeConstraint = (idx: number) => {
    setForm(prev => ({ ...prev, constraints: prev.constraints.filter((_, i) => i !== idx) }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const result = await createContext(form);
      const context = {
        ...result,
        problem_id: problemId,
        createdAt: new Date().toISOString(),
      };
      dispatch({ type: 'ADD_CONTEXT', payload: context });
      onSuccess?.();
      setForm({ problem_id: problemId, industry: '', company_size: '', decision_actor: '', extra: '', constraints: [] });
    } catch (err: any) {
      setError(err?.message || 'Failed to create context');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto">
      {/* Premium Form Card */}
      <div className="form-card">
        {/* Card Header */}
        <div className="form-card-header">
          <div className="flex items-center gap-4 mb-2">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
              <Building2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Add New Context</h2>
              <p className="text-sm text-slate-500 mt-0.5">Define the business context for this problem</p>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mx-8 mt-4">
            <div className="alert-premium alert-error">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          </div>
        )}

        {/* Form Body */}
        <div className="form-card-body">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="input-label-premium">Industry</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                  <input
                    className="input-premium pl-10"
                    value={form.industry}
                    onChange={e => setForm(prev => ({ ...prev, industry: e.target.value }))}
                    placeholder="e.g. SaaS"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="input-label-premium">Company Size</label>
                <div className="relative">
                  <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                  <input
                    className="input-premium pl-10"
                    value={form.company_size}
                    onChange={e => setForm(prev => ({ ...prev, company_size: e.target.value }))}
                    placeholder="e.g. 50-200 employees"
                    required
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="input-label-premium">Decision Actor</label>
              <div className="relative">
                <UserCog className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
                <input
                  className="input-premium pl-10"
                  value={form.decision_actor}
                  onChange={e => setForm(prev => ({ ...prev, decision_actor: e.target.value }))}
                  placeholder="e.g. Head of Growth"
                  required
                />
              </div>
            </div>

            <div>
              <label className="input-label-premium">Extra Context (optional)</label>
              <div className="relative">
                <FileText className="absolute left-3 top-3 w-4 h-4 text-slate-600" />
                <textarea
                  className="input-premium pl-10"
                  value={form.extra}
                  onChange={e => setForm(prev => ({ ...prev, extra: e.target.value }))}
                  placeholder="Any additional context..."
                  rows={3}
                />
              </div>
            </div>

            <div>
              <label className="input-label-premium">Constraints</label>
              <div className="flex gap-2 mb-3">
                <input
                  className="input-premium flex-1"
                  value={constraintInput}
                  onChange={e => setConstraintInput(e.target.value)}
                  placeholder="Add a constraint..."
                  onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addConstraint())}
                />
                <button type="button" onClick={addConstraint} className="btn-premium btn-premium-secondary px-4">
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {form.constraints.map((c, i) => (
                  <span key={i} className="constraint-tag">
                    {c}
                    <button type="button" onClick={() => removeConstraint(i)}>
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
                {form.constraints.length === 0 && (
                  <p className="text-xs text-slate-600 italic">No constraints added yet</p>
                )}
              </div>
            </div>
          </form>
        </div>

        {/* Card Footer */}
        <div className="form-card-footer">
          <button
            type="button"
            onClick={onSuccess}
            className="btn-premium btn-premium-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={loading}
            className="btn-premium btn-premium-primary"
          >
            {loading ? (
              <>
                <div className="spinner-premium" />
                Creating...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Create Context
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}