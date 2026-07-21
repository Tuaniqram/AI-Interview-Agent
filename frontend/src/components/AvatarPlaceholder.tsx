import React from 'react';
import { Camera, CameraOff, Mic, CheckCircle, XCircle } from 'lucide-react';
import { useCamera } from '../hooks/useCamera';
import { voiceService } from '../services/voiceService';
import { apiClient } from '../services/apiClient';

interface Company {
  id: number;
  name: string;
  website?: string;
  description?: string;
}

interface AvatarPlaceholderProps {
  onInterviewStart: (params: { companyId: number; jobRole: string; interviewMode: string; totalQuestions: number }) => Promise<void>;
  modeConfig: { companyId: number; jobRole: string; apiURL: string };
  onModeConfigChange: (config: { companyId: number; jobRole: string; apiURL: string }) => void;
}

export function AvatarPlaceholder({
  onInterviewStart,
  modeConfig,
  onModeConfigChange
}: AvatarPlaceholderProps) {
  const [isSimulating, setIsSimulating] = React.useState(false);
  const [totalQuestions, setTotalQuestions] = React.useState<number>(10);
  const camera = useCamera();
  const [micTested, setMicTested] = React.useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const videoRef = React.useRef<HTMLVideoElement>(null);
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

  React.useEffect(() => {
    if (videoRef.current && camera.stream) {
      videoRef.current.srcObject = camera.stream;
    }
  }, [camera.stream]);

  const testMic = async () => {
    setMicTested('testing');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(t => t.stop());
      setMicTested('success');
    } catch {
      setMicTested('error');
    }
  };

  const handleStart = async () => {
    setIsSimulating(true);
    try {
      await onInterviewStart({
        companyId: modeConfig.companyId,
        jobRole: modeConfig.jobRole,
        interviewMode: 'avatar',
        totalQuestions
      });
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="min-h-[600px] bg-section rounded-2xl shadow-lg p-8 flex flex-col items-center">
      {/* Avatar Visualization */}
      <div className="relative mb-6">
        <div className="w-48 h-48 bg-action-primary/30 rounded-full flex items-center justify-center animate-pulse">
          <div className="w-40 h-40 bg-action-primary/40 rounded-full flex items-center justify-center">
          </div>
        </div>
        <div className="absolute bottom-4 right-4 w-6 h-6 bg-success rounded-full" />
      </div>

      <h2 className="text-3xl font-bold text-primary mb-2">AI Avatar Interview</h2>
      <p className="text-secondary text-center mb-6 max-w-md">
        AI avatar asks questions aloud. You can speak answers or type them.
        Camera preview shows your video (future emotion analysis).
      </p>

      {/* Device Permissions */}
      <div className="w-full max-w-2xl mb-6 grid grid-cols-2 gap-4">
        <div className="p-4 bg-section rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Camera className="w-5 h-5 text-secondary" />
              <span className="font-medium text-secondary text-sm">Camera</span>
            </div>
            <button
              onClick={camera.isCameraOn ? camera.stopCamera : camera.startCamera}
              className={`p-1.5 rounded-lg transition-all ${
                camera.isCameraOn
                  ? 'bg-success-bg text-success-text'
                  : 'bg-input text-muted hover:bg-hover'
              }`}
            >
              {camera.isCameraOn ? <CheckCircle className="w-4 h-4" /> : <CameraOff className="w-4 h-4" />}
            </button>
          </div>
          {camera.stream ? (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-24 rounded-lg object-cover scale-x-[-1] bg-page"
            />
          ) : (
            <div className="w-full h-24 bg-input rounded-lg flex items-center justify-center text-muted text-xs">
              {camera.isPermissionDenied ? 'Permission denied' : 'Click to enable'}
            </div>
          )}
          {camera.error && <p className="text-error-text text-xs mt-1">{camera.error}</p>}
        </div>

        <div className="p-4 bg-section rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Mic className="w-5 h-5 text-secondary" />
              <span className="font-medium text-secondary text-sm">Microphone</span>
            </div>
            <button
              onClick={testMic}
              disabled={micTested === 'testing'}
              className={`p-1.5 rounded-lg transition-all ${
                micTested === 'success'
                  ? 'bg-success-bg text-success-text'
                  : micTested === 'error'
                  ? 'bg-error-bg text-error-text'
                  : 'bg-input text-muted hover:bg-hover'
              } disabled:opacity-50`}
            >
              {micTested === 'idle' && <Mic className="w-4 h-4" />}
              {micTested === 'testing' && <span className="w-4 h-4 block animate-spin rounded-full" />}
              {micTested === 'success' && <CheckCircle className="w-4 h-4" />}
              {micTested === 'error' && <XCircle className="w-4 h-4" />}
            </button>
          </div>
          <div className="w-full h-24 bg-input rounded-lg flex items-center justify-center text-muted text-xs">
            {micTested === 'idle' && 'Test your microphone'}
            {micTested === 'testing' && 'Testing...'}
            {micTested === 'success' && 'Microphone working'}
            {micTested === 'error' && 'Microphone not detected'}
          </div>
          {!voiceService.isSupported && (
            <p className="text-warning text-xs mt-1">Voice not supported in this browser</p>
          )}
        </div>
      </div>

      {/* Configuration */}
      <div className="w-full max-w-2xl mb-8">
        <h3 className="text-lg font-semibold text-primary mb-4">Configuration</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-secondary mb-2">
              Company
            </label>
            <select
              value={modeConfig.companyId}
              onChange={(e) => onModeConfigChange({ ...modeConfig, companyId: Number(e.target.value) })}
              disabled={companiesLoading}
              className="w-full px-4 py-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] transition-all bg-input text-primary"
            >
              {companiesLoading && <option value="">Loading companies...</option>}
              {!companiesLoading && companies.length === 0 && <option value="">No companies found</option>}
              {companies.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary mb-2">
              Job Role
            </label>
            <input
              type="text"
              value={modeConfig.jobRole}
              onChange={(e) => onModeConfigChange({ ...modeConfig, jobRole: e.target.value })}
              placeholder="e.g., AI Research Engineer"
              className="w-full px-4 py-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] transition-all bg-input text-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary mb-2">
              Number of Questions
            </label>
            <select
              value={totalQuestions}
              onChange={(e) => setTotalQuestions(Number(e.target.value))}
              className="w-full px-4 py-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] transition-all bg-input text-primary"
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
        disabled={isSimulating}
        className="w-full py-3.5 bg-action-primary text-inverse rounded-xl font-semibold text-lg hover:bg-action-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl max-w-2xl"
      >
        {isSimulating ? (
          <>
            Initializing Avatar Interview...
          </>
        ) : (
          <>
            Start Avatar Interview
          </>
        )}
      </button>
    </div>
  );
}
