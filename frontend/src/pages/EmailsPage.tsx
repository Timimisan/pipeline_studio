import { Link } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Mail, ArrowRight, Calendar, Search, Filter } from 'lucide-react';
import { useState } from 'react';

export default function EmailsPage() {
  const { state } = useApp();
  const [searchTerm, setSearchTerm] = useState('');

  const filteredEmails = state.emails.filter(e =>
    e?.subject_line?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    e?.problemName?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="page-title">Generated Emails</h1>
          <p className="page-subtitle">History of all pipeline executions</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
            <input
              type="text"
              placeholder="Search emails..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="input-premium pl-10 w-64 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Emails List */}
      <div className="glass-card overflow-hidden">
        {filteredEmails.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-4">
              <Mail className="w-8 h-8 text-slate-600" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-1">No emails yet</h3>
            <p className="text-sm text-slate-500 max-w-sm mx-auto">
              {searchTerm ? 'No emails match your search.' : 'Run a pipeline from a problem page to generate your first email.'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-white/[0.04]">
            {filteredEmails.map(email => (
              <Link
                key={email.id}
                to={`/emails/${email.id}`}
                className="block p-6 hover:bg-white/[0.02] transition-all group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shrink-0">
                        <Mail className="w-4 h-4 text-white" />
                      </div>
                      <h3 className="font-semibold text-white group-hover:text-indigo-300 transition-colors truncate">
                        {email.subject_line}
                      </h3>
                    </div>
                    <p className="text-sm text-slate-500 line-clamp-2 leading-relaxed ml-11">
                      {email.email}
                    </p>
                    <div className="flex items-center gap-4 mt-3 ml-11 text-xs text-slate-600">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-3 h-3" />
                        {new Date(email.createdAt).toLocaleDateString()}
                      </span>
                      <span className="px-2 py-0.5 bg-slate-800/50 rounded text-slate-500">
                        {email.problemName}
                      </span>
                      <span className="px-2 py-0.5 bg-slate-800/50 rounded text-slate-500">
                        {email.contextName}
                      </span>
                      <span className="text-[10px] font-mono text-slate-700">
                        ID: {email.final_email_id}
                      </span>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-slate-700 group-hover:text-indigo-400 transition-colors shrink-0 mt-2" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}