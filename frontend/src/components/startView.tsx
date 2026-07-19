import React from 'react';
import { Loader2 } from 'lucide-react';
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

/**
 * Start View Component
 * Displays the initial interview setup screen where users select their interview mode and configuration
 */
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

  const handleModeSelect = (mode: string) => {
    setSelectedMode(mode);
    setError(null);
  };

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

  const handleConfigChange = (field: keyof typeof modeConfig, value: string) => {
    onModeConfigChange({ ...modeConfig, [field]: value });
  };

  return (
    <div className="min-h-[600px] bg-white rounded-2xl shadow-lg p-8">
      <div className="text-center mb-8">
        <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-4xl">🎯</span>
        </div>
        <h2 className="text-3xl font-bold text-gray-800 mb-2">AI Interview Agent</h2>
        <p className="text-gray-600">Select your interview mode and configure your session</p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
          <div className="flex items-center gap-2 text-red-700">
            <span>❌</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Mode Selection */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Select Mode</h3>
        <div className="grid grid-cols-2 gap-4">
          {[
            { id: 'typing', label: 'Typing Mode', icon: '📝', description: 'Traditional text-based interview' },
            { id: 'voice', label: 'Voice Mode', icon: '🎤', description: 'Speech-to-text interview evaluation' },
            { id: 'avatar', label: 'Avatar Mode', icon: '🎭', description: 'AI avatar interviewer' },
            { id: 'realtime', label: 'Real-time', icon: '💬', description: 'Live conversation (coming soon)' },
          ].map((mode) => (
            <button
              key={mode.id}
              onClick={() => handleModeSelect(mode.id)}
              className={`p-4 rounded-xl border-2 text-left transition-all ${
                selectedMode === mode.id
                  ? 'border-purple-600 bg-purple-50'
                  : 'border-gray-200 hover:border-purple-300'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{mode.icon}</span>
                <span className="font-semibold text-gray-800">{mode.label}</span>
              </div>
              <p className="text-sm text-gray-600">{mode.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Configuration */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Configuration</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Company
            </label>
            <select
              value={modeConfig.companyId}
              onChange={(e) => onModeConfigChange({ ...modeConfig, companyId: Number(e.target.value) })}
              disabled={companiesLoading}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
            >
              {companiesLoading && <option value="">Loading companies...</option>}
              {!companiesLoading && companies.length === 0 && <option value="">No companies found</option>}
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Job Role
            </label>
            <input
              type="text"
              value={modeConfig.jobRole}
              onChange={(e) => handleConfigChange('jobRole', e.target.value)}
              placeholder="e.g., Software Engineer"
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              API URL
            </label>
            <input
              type="text"
              value={modeConfig.apiURL}
              onChange={(e) => handleConfigChange('apiURL', e.target.value)}
              placeholder="http://localhost:8000"
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all font-mono text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Questions
            </label>
            <select
              value={totalQuestions}
              onChange={(e) => setTotalQuestions(Number(e.target.value))}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
            >
              <option value={5}>5 questions (Quick)</option>
              <option value={10}>10 questions (Standard)</option>
              <option value={15}>15 questions (Detailed)</option>
              <option value={20}>20 questions (Comprehensive)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Start Button */}
      <button
        onClick={handleStart}
        disabled={isStarting}
        className="w-full py-3.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl font-semibold text-lg hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl"
      >
        {isStarting ? (
          <>
            <Loader2 className="animate-spin w-5 h-5 inline-block mr-2" />
            Starting Interview...
          </>
        ) : (
          <>
            Start Interview
            <span className="ml-2 text-2xl">🚀</span>
          </>
        )}
      </button>
    </div>
  );
}