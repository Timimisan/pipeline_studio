import { useState } from 'react';
import { Copy, Check, Mail, Download } from 'lucide-react';

interface Props {
  subject: string;
  body: string;
  emailId: number;
}

export default function EmailViewer({ subject, body, emailId }: Props) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(`Subject: ${subject}

${body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadEmail = () => {
    const blob = new Blob([`Subject: ${subject}

${body}`], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `email-${emailId}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="email-viewer">
      {/* Header */}
      <div className="email-viewer-header flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
            <Mail className="w-5 h-5 text-indigo-300" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Generated Email</h3>
            <p className="text-xs text-indigo-300/60 font-mono">ID: {emailId}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={downloadEmail}
            className="flex items-center gap-2 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-xs text-slate-400 hover:text-white transition-all border border-white/10"
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </button>
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-2 px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-lg text-xs text-slate-400 hover:text-white transition-all border border-white/10"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        <div className="mb-6 pb-6 border-b border-white/[0.06]">
          <label className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-2 block">Subject Line</label>
          <p className="text-lg font-semibold text-white">{subject}</p>
        </div>

        <div>
          <label className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mb-3 block">Body</label>
          <div className="email-body rounded-xl">
            {body}
          </div>
        </div>
      </div>
    </div>
  );
}