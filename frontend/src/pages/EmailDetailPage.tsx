import { useParams, Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import EmailViewer from '../components/EmailViewer';
import ValidationDashboard from '../components/ValidationDashboard';
import { ArrowLeft, Calendar, Hash, FileText, Building2 } from 'lucide-react';

export default function EmailDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { state } = useApp();

  const email = state.emails.find(e => String(e?.id) === id);

  if (!state.hydrated) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!email) {
    return (
      <div className="text-center py-20">
        <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
          <FileText className="w-8 h-8 text-slate-600" />
        </div>
        <h2 className="text-xl font-semibold text-white">Email not found</h2>
        <p className="text-slate-500 mt-2 text-sm">This email may have been generated in a different session.</p>
        <Link to="/emails" className="mt-6 inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 text-sm font-medium transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to emails
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <Link
          to="/emails"
          className="inline-flex items-center gap-2 text-slate-500 hover:text-white transition-colors mb-4 text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Emails
        </Link>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <FileText className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Email Details</h1>
            <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3 h-3" />
                {email.createdAt ? new Date(email.createdAt).toLocaleString() : '—'}
              </span>
              <span className="flex items-center gap-1.5">
                <Hash className="w-3 h-3" />
                {email.final_email_id}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Meta Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Problem</p>
            <p className="text-sm font-medium text-white mt-0.5">{email.problemName || '—'}</p>
          </div>
        </div>
        <div className="glass-card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center shrink-0">
            <Building2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Context</p>
            <p className="text-sm font-medium text-white mt-0.5">{email.contextName || '—'}</p>
          </div>
        </div>
        <div className="glass-card p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shrink-0">
            <Hash className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Email ID</p>
            <p className="text-sm font-medium text-white mt-0.5">{email.final_email_id}</p>
          </div>
        </div>
      </div>

      {/* Email Viewer */}
      <EmailViewer
        subject={email.subject_line || ''}
        body={email.email || ''}
        emailId={email.final_email_id}
      />

      {/* Validation Dashboard */}
      <ValidationDashboard
        scores={email.validation_scores || {}}
        attempts={email.attempts || {}}
      />
    </div>
  );
}