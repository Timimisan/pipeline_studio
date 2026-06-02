import ProblemForm from '../components/ProblemForm';
import { Target } from 'lucide-react';

export default function NewProblemPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
            <Target className="w-4 h-4 text-white" />
          </div>
          <h1 className="page-title">Create New Problem</h1>
        </div>
        <p className="page-subtitle">Define the operational failure pattern, contradiction, and solution mechanism.</p>
      </div>
      <ProblemForm />
    </div>
  );
}