import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createProblem } from '../api/client';
import { useApp } from '../context/AppContext';
import type { CreateProblemRequest } from '../types';
import { Save, AlertCircle, Sparkles, Brain, Zap, GitBranch, Target, Lightbulb, ArrowLeft } from 'lucide-react';

const initialForm: CreateProblemRequest = {
  problem_name: '',
  core_problem: '',
  system: '',
  causal_mechanism: '',
  failure_mode_A: '',
  failure_mode_B: '',
  failure_mode_A_mechanism: '',
  failure_mode_B_mechanism: '',
  contradiction: '',
  business_impact: '',
  solution_mechanism: '',
  solution_actor: '',
};

export default function ProblemForm() {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { dispatch } = useApp();
  const navigate = useNavigate();

  const update = (field: keyof CreateProblemRequest, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const result = await createProblem(form);
      const problem = {
        ...result,
        createdAt: new Date().toISOString(),
        fullData: form,
      };
      dispatch({ type: 'ADD_PROBLEM', payload: problem });
      navigate(`/problems/${result.problem_id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const sections = [
    {
      title: 'Problem Identity',
      icon: Sparkles,
      color: 'from-blue-500 to-cyan-500',
      fields: [
        { key: 'problem_name' as const, label: 'Problem Name', type: 'text', placeholder: 'e.g. AI Outreach Instability' },
        { key: 'system' as const, label: 'System', type: 'text', placeholder: 'e.g. AI-powered outbound email system' },
        { key: 'core_problem' as const, label: 'Core Problem', type: 'textarea', placeholder: 'Describe the fundamental operational failure...' },
      ]
    },
    {
      title: 'Failure Modes',
      icon: GitBranch,
      color: 'from-red-500 to-orange-500',
      fields: [
        { key: 'failure_mode_A' as const, label: 'Failure Mode A', type: 'textarea', placeholder: 'e.g. Personalization decay under prompt iteration' },
        { key: 'failure_mode_A_mechanism' as const, label: 'Failure Mode A Mechanism', type: 'textarea', placeholder: 'Causal mechanism behind Mode A...' },
        { key: 'failure_mode_B' as const, label: 'Failure Mode B', type: 'textarea', placeholder: 'e.g. System variance increases with specificity attempts' },
        { key: 'failure_mode_B_mechanism' as const, label: 'Failure Mode B Mechanism', type: 'textarea', placeholder: 'Causal mechanism behind Mode B...' },
      ]
    },
    {
      title: 'Analysis & Contradiction',
      icon: Brain,
      color: 'from-amber-500 to-yellow-500',
      fields: [
        { key: 'contradiction' as const, label: 'Contradiction', type: 'textarea', placeholder: 'The core tension between the two failure modes...' },
        { key: 'causal_mechanism' as const, label: 'Causal Mechanism', type: 'textarea', placeholder: 'Root cause driving both failure modes...' },
        { key: 'business_impact' as const, label: 'Business Impact', type: 'textarea', placeholder: 'Decision-level consequences...' },
      ]
    },
    {
      title: 'Solution Profile',
      icon: Lightbulb,
      color: 'from-emerald-500 to-teal-500',
      fields: [
        { key: 'solution_mechanism' as const, label: 'Solution Mechanism', type: 'textarea', placeholder: 'How the system is structurally stabilized...' },
        { key: 'solution_actor' as const, label: 'Solution Actor', type: 'text', placeholder: 'e.g. AI automation engineer' },
      ]
    },
  ];

  return (
    <div className="max-w-2xl mx-auto pb-12">
      {/* Back Button */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 text-slate-500 hover:text-white transition-colors mb-6 text-sm font-medium"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </button>

      {/* Premium Form Card */}
      <div className="form-card">
        {/* Card Header */}
        <div className="form-card-header">
          <div className="flex items-center gap-4 mb-2">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Target className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Create New Problem</h2>
              <p className="text-sm text-slate-500 mt-0.5">Define the operational failure pattern</p>
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
          <form onSubmit={handleSubmit}>
            {sections.map((section, sectionIdx) => (
              <div key={section.title} className="form-section-premium" style={{ animationDelay: `${sectionIdx * 50}ms` }}>
                <h3 className="form-section-title-premium">
                  <div className={`icon-wrapper bg-gradient-to-br ${section.color}`}>
                    <section.icon />
                  </div>
                  {section.title}
                </h3>
                <div className="space-y-5">
                  {section.fields.map((field) => (
                    <div key={field.key}>
                      <label className="input-label-premium">{field.label}</label>
                      {field.type === 'textarea' ? (
                        <textarea
                          className="input-premium"
                          value={form[field.key]}
                          onChange={e => update(field.key, e.target.value)}
                          placeholder={field.placeholder}
                          required
                          rows={3}
                        />
                      ) : (
                        <input
                          type="text"
                          className="input-premium"
                          value={form[field.key]}
                          onChange={e => update(field.key, e.target.value)}
                          placeholder={field.placeholder}
                          required
                        />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </form>
        </div>

        {/* Card Footer */}
        <div className="form-card-footer">
          <button
            type="button"
            onClick={() => navigate('/')}
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
                Create Problem
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}