import React from 'react';
import { Loader2, Sparkles, MessageSquare, Mic, Video, AlertCircle } from 'lucide-react';
import { apiClient } from '../services/apiClient';

interface Company {
  id: number;
  name: string;
  website?: string;
  description?: string;
}

interface StartViewProps {
  onInterviewStart: (params: { companyId: number; jobRole: string; interviewMode: string; totalQuestions: number }) => Promise<void>;
  modeConfig: { companyId: number; jobRole: string; apiURL: string };
  onModeConfigChange: (config: { companyId: number; jobRole: string; apiURL: string }) => void;
}

export default function StartView({
  onInterviewStart,
  modeConfig,
  onModeConfigChange
}: StartViewProps) {
  const [selectedMode, setSelectedMode] = React.useState<string>('typing');
  const [totalQuestions, setTotalQuestions] = React.useState<number>(10);
  const [isStarting, setIsStarting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [companies, setCompanies] = React.useState<Company[]>([]);
  const [companiesLoading, setCompaniesLoading] = React.useState(true);

  React.useEffect(() => {
    apiClient.get<Company[]>('/companies/')
      .then((data) => {
        setCompanies(data);
        if (data.length > 0 && modeConfig.companyId === 1001) {
          const match = data.find(c => c.id === modeConfig.companyId);
          if (!match) {
            onModeConfigChange({ ...modeConfig, companyId: data[0].id });
          }
        }
      })
      .catch(() => {})
      .finally(() => setCompaniesLoading(false));
  }, []);

  const handleStart = async () => {
    setIsStarting(true);
    setError(null);
    try {
      await onInterviewStart({
        companyId: modeConfig.companyId,
        jobRole: modeConfig.jobRole,
        interviewMode: selectedMode,
        totalQuestions
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start interview');
    } finally {
      setIsStarting(false);
    }
  };

  const modes = [
    { id: 'typing', label: 'Typing', icon: MessageSquare, description: 'Text-based interview' },
    { id: 'voice', label: 'Voice', icon: Mic, description: 'Speech-to-text evaluation' },
    { id: 'avatar', label: 'Avatar', icon: Video, description: '3D AI interviewer' },
  ];

  return (
    <div className="min-h-[600px] bg-elevated border border-default rounded-xl p-8">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-action-primary rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Sparkles className="w-8 h-8 text-inverse" />
        </div>
        <h2 className="text-2xl font-bold text-primary mb-1">AI Interview Agent</h2>
        <p className="text-sm text-secondary">Select your interview mode and configure your session</p>
      </div>

      {error && (
        <div className="mb-6 bg-error-bg border border-error/20 rounded-lg p-3 text-sm text-error-text flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="mb-8">
        <h3 className="text-sm font-semibold text-primary mb-3">Mode</h3>
        <div className="grid grid-cols-3 gap-3">
          {modes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setSelectedMode(mode.id)}
              className={`p-3 rounded-xl border-2 text-left transition-all ${
                selectedMode === mode.id
                  ? 'border-focus bg-action-primary/15'
                  : 'border-default hover:border-focus'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <mode.icon className="w-4 h-4 text-action-primary" />
                <span className="text-sm font-medium text-primary">{mode.label}</span>
              </div>
              <p className="text-xs text-muted">{mode.description}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="mb-8">
        <h3 className="text-sm font-semibold text-primary mb-3">Configuration</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Company</label>
            <select
              value={modeConfig.companyId}
              onChange={(e) => onModeConfigChange({ ...modeConfig, companyId: Number(e.target.value) })}
              disabled={companiesLoading}
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus transition-colors"
            >
              {companiesLoading && <option value="">Loading companies...</option>}
              {!companiesLoading && companies.length === 0 && <option value="">No companies found</option>}
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Job Role</label>
            <input
              type="text"
              value={modeConfig.jobRole}
              onChange={(e) => onModeConfigChange({ ...modeConfig, jobRole: e.target.value })}
              placeholder="e.g., Software Engineer"
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">API URL</label>
            <input
              type="text"
              value={modeConfig.apiURL}
              onChange={(e) => onModeConfigChange({ ...modeConfig, apiURL: e.target.value })}
              placeholder="http://localhost:8000"
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus transition-colors font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Number of Questions</label>
            <select
              value={totalQuestions}
              onChange={(e) => setTotalQuestions(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus transition-colors"
            >
              <option value={5}>5 questions (Quick)</option>
              <option value={10}>10 questions (Standard)</option>
              <option value={15}>15 questions (Detailed)</option>
              <option value={20}>20 questions (Comprehensive)</option>
            </select>
          </div>
        </div>
      </div>

      <button
        onClick={handleStart}
        disabled={isStarting}
        className="w-full py-3 bg-action-primary text-inverse rounded-xl font-semibold text-sm hover:bg-action-primary-hover active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
      >
        {isStarting ? (
          <span className="inline-flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Starting Interview...
          </span>
        ) : (
          'Start Interview'
        )}
      </button>
    </div>
  );
}
