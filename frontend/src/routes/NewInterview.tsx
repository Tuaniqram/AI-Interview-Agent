import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { useInterviewStore } from '../state/interviewStore';
import { Card } from '../components/shared/Card';

interface Company {
  id: number;
  name: string;
  website?: string;
  description?: string;
}

export function NewInterview() {
  const navigate = useNavigate();
  const { actions } = useInterviewStore();
  const [selectedMode, setSelectedMode] = React.useState('avatar');
  const [companyId, setCompanyId] = React.useState<number>(0);
  const [jobRole, setJobRole] = React.useState('Software Engineer');
  const [totalQuestions, setTotalQuestions] = React.useState(10);
  const [isStarting, setIsStarting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [companies, setCompanies] = React.useState<Company[]>([]);
  const [companiesLoading, setCompaniesLoading] = React.useState(true);

  React.useEffect(() => {
    apiClient.get<Company[]>('/companies/')
      .then(data => {
        setCompanies(data);
        if (data.length > 0) setCompanyId(data[0].id);
      })
      .catch(() => {})
      .finally(() => setCompaniesLoading(false));
  }, []);

  const handleStart = async () => {
    setIsStarting(true);
    setError(null);
    try {
      await actions.startInterview({ companyId, jobRole, totalQuestions });
      navigate('/interview/active');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start interview');
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8">
      <Card padding="lg">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-action-primary rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl text-inverse font-bold">AI</span>
          </div>
          <h2 className="text-2xl font-bold text-primary mb-1">New Interview</h2>
          <p className="text-sm text-secondary">Configure your AI interview session</p>
        </div>

        {error && (
          <div className="mb-6 bg-error-bg border border-error/20 rounded-lg p-3 text-sm text-error-text">
            {error}
          </div>
        )}

        <div className="mb-6">
          <h3 className="text-sm font-semibold text-primary mb-3">Mode</h3>
          <div className="grid grid-cols-3 gap-3">
            {[
              { id: 'typing', label: 'Typing', desc: 'Text-based' },
              { id: 'voice', label: 'Voice', desc: 'Speech-to-text' },
              { id: 'avatar', label: 'Avatar', desc: '3D AI interviewer' },
            ].map(m => (
              <button key={m.id} onClick={() => setSelectedMode(m.id)}
                className={`p-3 rounded-xl border-2 text-left transition-all ${
                  selectedMode === m.id
                    ? 'border-focus bg-action-primary/15'
                    : 'border-default hover:border-focus'
                }`}>
                <div className="text-sm font-medium text-primary">{m.label}</div>
                <div className="text-xs text-muted">{m.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Company</label>
            <select value={companyId} onChange={e => setCompanyId(Number(e.target.value))} disabled={companiesLoading}
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus">
              {companiesLoading && <option>Loading...</option>}
              {companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Job Role</label>
            <input type="text" value={jobRole} onChange={e => setJobRole(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus" />
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Questions</label>
            <select value={totalQuestions} onChange={e => setTotalQuestions(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus">
              {[5, 10, 15, 20].map(n => <option key={n} value={n}>{n} questions</option>)}
            </select>
          </div>
        </div>

        <button onClick={handleStart} disabled={isStarting || !companyId}
          className="w-full py-3 bg-action-primary text-inverse rounded-xl font-semibold text-sm hover:bg-action-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md">
          {isStarting ? <><Loader2 className="animate-spin w-4 h-4 inline mr-2" />Starting...</> : 'Start Interview'}
        </button>
      </Card>
    </div>
  );
}
