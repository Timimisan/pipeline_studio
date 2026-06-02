import { useEffect, useState } from 'react';
import { Brain, Type, Anchor, Zap, HelpCircle, Shield, MessageSquare, Mail, Loader2 } from 'lucide-react';

const stages = [
  { key: 'reasoning_state', label: 'Reasoning', icon: Brain, desc: 'Contextualized failure modes & contradiction', gradient: 'from-purple-500 to-fuchsia-500' },
  { key: 'subject_line', label: 'Subject', icon: Type, desc: 'Pain-hinted subject line', gradient: 'from-blue-500 to-cyan-500' },
  { key: 'hook', label: 'Hook', icon: Anchor, desc: 'Operational tension opener', gradient: 'from-indigo-500 to-violet-500' },
  { key: 'tension', label: 'Tension', icon: Zap, desc: 'Compressed contradiction implication', gradient: 'from-amber-500 to-orange-500' },
  { key: 'transition_question', label: 'Transition', icon: HelpCircle, desc: 'Bridge into authority', gradient: 'from-pink-500 to-rose-500' },
  { key: 'authority', label: 'Authority', icon: Shield, desc: 'Stabilization mechanism', gradient: 'from-emerald-500 to-teal-500' },
  { key: 'cta', label: 'CTA', icon: MessageSquare, desc: 'Diagnostic recognition check', gradient: 'from-cyan-500 to-sky-500' },
  { key: 'final_assembly', label: 'Assembly', icon: Mail, desc: 'Flow optimization', gradient: 'from-slate-500 to-slate-400' },
] as const;

export default function PipelineVisualizer() {
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStage(prev => (prev < stages.length - 1 ? prev + 1 : prev));
    }, 800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-bold text-slate-600 uppercase tracking-widest mb-6">
        Pipeline Execution
      </h3>
      <div className="relative">
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gradient-to-b from-indigo-500/20 via-purple-500/20 to-transparent" />
        <div className="space-y-4">
          {stages.map((stage, idx) => {
            const Icon = stage.icon;
            const isActive = idx <= activeStage;
            const isCurrent = idx === activeStage;

            return (
              <div key={stage.key} className={`relative flex items-center gap-4 pl-14 transition-all duration-500 ${isActive ? 'opacity-100' : 'opacity-30'}`}>
                <div className={`absolute left-2 w-7 h-7 rounded-full border-2 flex items-center justify-center bg-[#0a0a0f] z-10 transition-all duration-300 ${
                  isCurrent ? 'border-indigo-500 shadow-lg shadow-indigo-500/30' :
                  isActive ? 'border-emerald-500/50' : 'border-slate-700'
                }`}>
                  {isCurrent ? <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" /> :
                   isActive ? <div className="w-2 h-2 rounded-full bg-emerald-400" /> : null}
                </div>

                <div className={`p-4 rounded-xl border flex-1 transition-all duration-500 ${
                  isCurrent ? 'border-indigo-500/20 bg-indigo-500/5 shadow-lg shadow-indigo-500/10' :
                  isActive ? 'border-emerald-500/10 bg-emerald-500/[0.02]' : 'border-white/[0.04] bg-white/[0.01]'
                }`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${stage.gradient} flex items-center justify-center shadow-md`}>
                      <Icon className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`font-semibold text-sm ${isCurrent ? 'text-indigo-300' : isActive ? 'text-emerald-300' : 'text-slate-500'}`}>
                          {stage.label}
                        </span>
                        {isCurrent && <span className="text-[10px] text-indigo-400 animate-pulse font-medium">Processing...</span>}
                      </div>
                      <p className="text-xs text-slate-600 mt-0.5">{stage.desc}</p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}