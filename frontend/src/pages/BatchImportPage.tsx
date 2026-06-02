import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import {
  Upload, Database, FileSpreadsheet, Link2, ChevronRight,
  CheckCircle, AlertCircle, Loader2, Building2, Settings,
  ArrowLeft, Zap, Table, X
} from 'lucide-react';

// ─── Sub-components ───

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`glass-card p-6 ${className}`}>{children}</div>;
}

function SectionTitle({ icon: Icon, title, subtitle }: { icon: any; title: string; subtitle: string }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
        <Icon className="w-4 h-4 text-white" />
      </div>
      <div>
        <h3 className="font-semibold text-white">{title}</h3>
        <p className="text-xs text-slate-500">{subtitle}</p>
      </div>
    </div>
  );
}

function InputGroup({ label, children, icon: Icon }: { label: string; children: React.ReactNode; icon?: any }) {
  return (
    <div className="space-y-2">
      <label className="input-label-premium flex items-center gap-2">
        {Icon && <Icon className="w-3.5 h-3.5 text-slate-600" />}
        {label}
      </label>
      {children}
    </div>
  );
}

// ─── Main Page ───

export default function BatchImportPage() {
  const { state } = useApp();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);

  // Source selection
  const [source, setSource] = useState<'csv' | 'google_sheets' | 'airtable' | null>(null);

  // Problem selection
  const [selectedProblemId, setSelectedProblemId] = useState('');

  // CSV state
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [columnMapping, setColumnMapping] = useState({
    industry: 'Sector',
    company_size: 'Size',
    decision_actor: 'Role',
    extra: 'Notes',
    constraints: 'Tags',
  });
  const [mappingJson, setMappingJson] = useState('');

  // CRM state
  const [crmConfig, setCrmConfig] = useState('');
  const [crmConfigJson, setCrmConfigJson] = useState('');

  // Results / loading
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);

  const problems = state.problems;

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    if (file && !file.name.endsWith('.csv')) {
      setError('Please upload a .csv file');
      setCsvFile(null);
      return;
    }
    setError('');
    setCsvFile(file);
  };

  const buildMapping = () => {
    try {
      if (mappingJson.trim()) {
        return JSON.parse(mappingJson);
      }
      const m: Record<string, string> = {};
      Object.entries(columnMapping).forEach(([k, v]) => {
        if (v.trim()) m[k] = v.trim();
      });
      return m;
    } catch {
      throw new Error('Invalid column mapping JSON');
    }
  };

  const buildCrmConfig = () => {
    try {
      if (crmConfigJson.trim()) {
        return JSON.parse(crmConfigJson);
      }
      return JSON.parse(crmConfig || '{}');
    } catch {
      throw new Error('Invalid CRM config JSON');
    }
  };

  const handleImport = async () => {
    if (!selectedProblemId) {
      setError('Select a problem first');
      return;
    }
    if (!source) {
      setError('Choose an import source');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      if (source === 'csv') {
        if (!csvFile) {
          setError('Upload a CSV file');
          setLoading(false);
          return;
        }
        const form = new FormData();
        form.append('problem_id', selectedProblemId);
        form.append('column_mapping', JSON.stringify(buildMapping()));
        form.append('file', csvFile);

        const res = await fetch(`${API_BASE}/import/csv`, {
          method: 'POST',
          body: form,
        });
        if (!res.ok) throw new Error(await res.text());
        setResult(await res.json());
      } else {
        const form = new FormData();
        form.append('problem_id', selectedProblemId);
        form.append('source', source);
        form.append('crm_config', JSON.stringify(buildCrmConfig()));
        form.append('column_mapping', JSON.stringify(buildMapping()));

        const res = await fetch(`${API_BASE}/import/crm`, {
          method: 'POST',
          body: form,
        });
        if (!res.ok) throw new Error(await res.text());
        setResult(await res.json());
      }
    } catch (err: any) {
      setError(err?.message || 'Import failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-2 text-slate-500 hover:text-white transition-colors mb-4 text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="page-title">Batch Import</h1>
            <p className="page-subtitle">Import leads from CRM or CSV and run the pipeline at scale</p>
          </div>
          <div className="badge badge-info">
            <Zap className="w-3 h-3" />
            Bulk
          </div>
        </div>
      </div>

      {/* Step 1: Choose Problem */}
      <Card>
        <SectionTitle icon={Building2} title="1. Select Problem" subtitle="All imported contexts will be linked to this problem" />
        <div className="relative">
          <select
            className="input-premium select-premium w-full md:w-96"
            value={selectedProblemId}
            onChange={e => { setSelectedProblemId(e.target.value); setError(''); }}
          >
            <option value="">Choose a problem…</option>
            {problems.map(p => {
              const pid = String(p?.problem_id ?? p?.id ?? '');
              const name = p?.snapshot?.problem_name ?? p?.problem_name ?? 'Untitled';
              return <option key={pid} value={pid}>{name}</option>;
            })}
          </select>
        </div>
        {problems.length === 0 && (
          <div className="mt-4 text-sm text-amber-400/80 bg-amber-500/5 rounded-lg p-3 border border-amber-500/10 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            No problems found. <button onClick={() => navigate('/problems/new')} className="underline hover:text-amber-300">Create one first</button>.
          </div>
        )}
      </Card>

      {/* Step 2: Choose Source */}
      <Card>
        <SectionTitle icon={Database} title="2. Import Source" subtitle="Connect a CRM or upload a spreadsheet" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {([
            { key: 'csv', label: 'CSV Upload', icon: Upload, desc: 'Spreadsheet file' },
            { key: 'google_sheets', label: 'Google Sheets', icon: Table, desc: 'Live sheet connection' },
            { key: 'airtable', label: 'Airtable', icon: Database, desc: 'Airtable base' },
          ] as const).map((opt) => {
            const active = source === opt.key;
            return (
              <button
                key={opt.key}
                onClick={() => { setSource(opt.key); setError(''); }}
                className={`relative p-5 rounded-xl border text-left transition-all ${
                  active
                    ? 'border-indigo-500/30 bg-indigo-500/5 shadow-lg shadow-indigo-500/10'
                    : 'border-white/[0.04] bg-white/[0.01] hover:border-white/[0.08] hover:bg-white/[0.02]'
                }`}
              >
                {active && (
                  <div className="absolute top-3 right-3">
                    <CheckCircle className="w-4 h-4 text-indigo-400" />
                  </div>
                )}
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${
                  active ? 'bg-gradient-to-br from-indigo-500 to-purple-500' : 'bg-slate-800'
                }`}>
                  <opt.icon className={`w-5 h-5 ${active ? 'text-white' : 'text-slate-500'}`} />
                </div>
                <h4 className={`font-semibold text-sm ${active ? 'text-indigo-300' : 'text-white'}`}>{opt.label}</h4>
                <p className="text-xs text-slate-500 mt-1">{opt.desc}</p>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Step 3: Configure Source */}
      {source === 'csv' && (
        <Card>
          <SectionTitle icon={FileSpreadsheet} title="3. CSV Configuration" subtitle="Map columns and upload your file" />
          <div className="space-y-6">
            {/* File Drop */}
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-white/[0.06] rounded-xl p-8 text-center hover:border-indigo-500/30 hover:bg-indigo-500/[0.02] transition-all cursor-pointer"
            >
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileSelect}
              />
              <Upload className="w-8 h-8 text-slate-600 mx-auto mb-3" />
              <p className="text-sm font-medium text-white">
                {csvFile ? csvFile.name : 'Click to upload .csv'}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {csvFile ? `${(csvFile.size / 1024).toFixed(1)} KB` : 'Must include headers'}
              </p>
            </div>

            {/* Column Mapping */}
            <div className="bg-white/[0.02] rounded-xl border border-white/[0.04] p-5">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Settings className="w-4 h-4 text-slate-500" />
                  Column Mapping
                </h4>
                <button
                  onClick={() => setMappingJson(mappingJson ? '' : JSON.stringify(columnMapping, null, 2))}
                  className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  {mappingJson ? 'Use simple fields' : 'Edit as JSON'}
                </button>
              </div>

              {mappingJson ? (
                <textarea
                  className="input-premium font-mono text-xs"
                  rows={6}
                  value={mappingJson}
                  onChange={e => setMappingJson(e.target.value)}
                  placeholder={`{\n  "industry": "Sector",\n  "company_size": "Size",\n  ...\n}`}
                />
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(columnMapping).map(([key, val]) => (
                    <InputGroup key={key} label={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}>
                      <input
                        className="input-premium"
                        value={val}
                        onChange={e => setColumnMapping(prev => ({ ...prev, [key]: e.target.value }))}
                        placeholder={`CSV column name for ${key}`}
                      />
                    </InputGroup>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {source === 'google_sheets' && (
        <Card>
          <SectionTitle icon={Link2} title="3. Google Sheets Connection" subtitle="Provide sheet ID and range" />
          <div className="space-y-5">
            <InputGroup label="Sheet Config (JSON)" icon={Settings}>
              <textarea
                className="input-premium font-mono text-xs"
                rows={5}
                value={crmConfigJson}
                onChange={e => setCrmConfigJson(e.target.value)}
                placeholder={`{\n  "sheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",\n  "range": "Sheet1!A1:Z1000",\n  "api_key": "YOUR_API_KEY"\n}`}
              />
            </InputGroup>
            <div className="bg-white/[0.02] rounded-xl border border-white/[0.04] p-5">
              <h4 className="text-sm font-semibold text-white mb-4">Column Mapping</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(columnMapping).map(([key, val]) => (
                  <InputGroup key={key} label={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}>
                    <input
                      className="input-premium"
                      value={val}
                      onChange={e => setColumnMapping(prev => ({ ...prev, [key]: e.target.value }))}
                      placeholder={`Sheet column name`}
                    />
                  </InputGroup>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {source === 'airtable' && (
        <Card>
          <SectionTitle icon={Database} title="3. Airtable Connection" subtitle="Base ID, table name, and API token" />
          <div className="space-y-5">
            <InputGroup label="Airtable Config (JSON)" icon={Settings}>
              <textarea
                className="input-premium font-mono text-xs"
                rows={5}
                value={crmConfigJson}
                onChange={e => setCrmConfigJson(e.target.value)}
                placeholder={`{\n  "base_id": "appXXXXXXXXXXXXXX",\n  "table_name": "Leads",\n  "api_token": "patXXXXXXXX.XXXXXXXX"\n}`}
              />
            </InputGroup>
            <div className="bg-white/[0.02] rounded-xl border border-white/[0.04] p-5">
              <h4 className="text-sm font-semibold text-white mb-4">Column Mapping</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(columnMapping).map(([key, val]) => (
                  <InputGroup key={key} label={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}>
                    <input
                      className="input-premium"
                      value={val}
                      onChange={e => setColumnMapping(prev => ({ ...prev, [key]: e.target.value }))}
                      placeholder={`Airtable field name`}
                    />
                  </InputGroup>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Error */}
      {error && (
        <div className="alert-premium alert-error flex items-start gap-3">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Import Error</p>
            <p className="text-xs text-red-300/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <Card className="border-emerald-500/20 bg-emerald-500/[0.02]">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <h3 className="font-semibold text-emerald-400">Import Successful</h3>
              <p className="text-xs text-slate-500">{result.message}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white/[0.02] rounded-lg p-3">
              <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Imported</p>
              <p className="text-lg font-bold text-white mt-1">{result.total_imported}</p>
            </div>
            <div className="bg-white/[0.02] rounded-lg p-3">
              <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Source</p>
              <p className="text-lg font-bold text-white mt-1 capitalize">{result.source}</p>
            </div>
            <div className="bg-white/[0.02] rounded-lg p-3 md:col-span-2">
              <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Problem ID</p>
              <p className="text-sm font-mono text-slate-300 mt-1 truncate">{result.problem_id}</p>
            </div>
          </div>
          {result.context_ids && result.context_ids.length > 0 && (
            <div className="mt-4">
              <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-2">Context IDs</p>
              <div className="flex flex-wrap gap-2">
                {result.context_ids.slice(0, 8).map((cid: string) => (
                  <span key={cid} className="text-[10px] font-mono text-slate-500 bg-slate-800/50 px-2 py-1 rounded truncate max-w-[200px]">
                    {cid}
                  </span>
                ))}
                {result.context_ids.length > 8 && (
                  <span className="text-[10px] text-slate-600">+{result.context_ids.length - 8} more</span>
                )}
              </div>
            </div>
          )}
          <div className="mt-5 flex gap-3">
            <button
              onClick={() => navigate(`/problems/${result.problem_id}`)}
              className="btn-premium btn-premium-primary text-sm"
            >
              <ChevronRight className="w-4 h-4" />
              Go to Problem
            </button>
            <button
              onClick={() => {
                setResult(null);
                setCsvFile(null);
                setError('');
              }}
              className="btn-premium btn-premium-secondary text-sm"
            >
              <X className="w-4 h-4" />
              Import More
            </button>
          </div>
        </Card>
      )}

      {/* Action Bar */}
      {!result && (
        <div className="flex items-center justify-end gap-4 pt-2">
          <button
            onClick={() => navigate('/')}
            className="btn-premium btn-premium-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={loading || !selectedProblemId || !source}
            className="btn-premium btn-premium-primary"
            style={{ opacity: (!loading && selectedProblemId && source) ? 1 : 0.5, cursor: (!loading && selectedProblemId && source) ? 'pointer' : 'not-allowed' }}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Importing…
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                Import {source === 'csv' ? 'CSV' : source === 'google_sheets' ? 'Sheet' : 'Airtable'}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}