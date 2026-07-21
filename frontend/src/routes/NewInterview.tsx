import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Bookmark, MessageSquare, Mic, Video } from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { useInterviewStore } from '../state/interviewStore';

interface Company {
  id: number;
  name: string;
  website?: string;
  description?: string;
}

interface Template {
  id: string;
  company_id: number;
  name: string;
  job_role: string;
  total_questions: number;
  interview_type: string;
}

const INPUT = 'w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus transition-colors';
const LABEL = 'block text-xs font-medium text-secondary mb-1.5';

export function NewInterview() {
  const navigate = useNavigate();
  const { actions } = useInterviewStore();
  const [selectedMode, setSelectedMode] = React.useState('avatar');
  const [companyId, setCompanyId] = React.useState<number>(0);
  const [jobRole, setJobRole] = React.useState('Software Engineer');
  const [totalQuestions, setTotalQuestions] = React.useState(10);
  const [candidateName, setCandidateName] = React.useState('');
  const [candidateEmail, setCandidateEmail] = React.useState('');
  const [isStarting, setIsStarting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [companies, setCompanies] = React.useState<Company[]>([]);
  const [companiesLoading, setCompaniesLoading] = React.useState(true);

  const [templates, setTemplates] = React.useState<Template[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = React.useState<string>('');
  const [saveAsTemplate, setSaveAsTemplate] = React.useState(false);
  const [templateName, setTemplateName] = React.useState('');

  React.useEffect(() => {
    apiClient.get<Company[]>('/companies/')
      .then(data => {
        setCompanies(data);
        if (data.length > 0) setCompanyId(data[0].id);
      })
      .catch(() => {})
      .finally(() => setCompaniesLoading(false));
  }, []);

  React.useEffect(() => {
    if (!companyId) return;
    apiClient.get<Template[]>(`/templates/?company_id=${companyId}`)
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, [companyId]);

  const handleTemplateChange = (templateId: string) => {
    setSelectedTemplateId(templateId);
    const t = templates.find(tmp => tmp.id === templateId);
    if (t) {
      setJobRole(t.job_role);
      setTotalQuestions(t.total_questions);
      setTemplateName(t.name);
    }
  };

  const handleStart = async () => {
    setIsStarting(true);
    setError(null);
    try {
      if (saveAsTemplate && templateName.trim()) {
        try {
          await apiClient.post('/templates/', {
            company_id: companyId,
            name: templateName.trim(),
            job_role: jobRole,
            total_questions: totalQuestions,
            interview_type: 'company',
          });
        } catch {}
      }

      await actions.startInterview({
        companyId,
        jobRole,
        totalQuestions,
        candidateName,
        candidateEmail,
        mode: selectedMode,
      });
      navigate('/interview/active');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start interview');
    } finally {
      setIsStarting(false);
    }
  };

  const modes = [
    { id: 'typing', label: 'Typing', icon: MessageSquare, desc: 'Text-based interview' },
    { id: 'voice', label: 'Voice', icon: Mic, desc: 'Speech-to-text' },
    { id: 'avatar', label: 'Avatar', icon: Video, desc: '3D AI interviewer' },
  ];

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-action-primary rounded-xl flex items-center justify-center">
          <span className="text-sm text-inverse font-bold">AI</span>
        </div>
        <div>
          <h1 className="text-xl font-semibold text-primary">New Interview</h1>
          <p className="text-sm text-secondary">Configure your AI interview session</p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 bg-error-bg border border-error/20 rounded-lg p-3 text-sm text-error-text">
          {error}
        </div>
      )}

      {/* Mode Selection */}
      <div className="mb-6">
        <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-3">Interview Mode</h3>
        <div className="grid grid-cols-3 gap-3">
          {modes.map(m => {
            const Icon = m.icon;
            const active = selectedMode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setSelectedMode(m.id)}
                className={`p-4 rounded-xl border-2 text-left transition-all ${
                  active
                    ? 'border-focus bg-action-primary/15 shadow-sm'
                    : 'border-default hover:border-strong hover:bg-hover'
                }`}
              >
                <div className="flex items-center gap-2.5 mb-1.5">
                  <Icon className={`w-5 h-5 ${active ? 'text-action-primary' : 'text-muted'}`} />
                  <span className="text-sm font-medium text-primary">{m.label}</span>
                </div>
                <p className="text-xs text-muted pl-7.5">{m.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Two-column form */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Left: Candidate info */}
        <div>
          <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-3">Candidate Info</h3>
          <div className="space-y-4">
            <div>
              <label className={LABEL}>Name</label>
              <input type="text" value={candidateName} onChange={e => setCandidateName(e.target.value)}
                placeholder="e.g. John Doe" className={INPUT} />
            </div>
            <div>
              <label className={LABEL}>Email</label>
              <input type="email" value={candidateEmail} onChange={e => setCandidateEmail(e.target.value)}
                placeholder="e.g. john@example.com" className={INPUT} />
            </div>
          </div>
        </div>

        {/* Right: Interview config */}
        <div>
          <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-3">Interview Config</h3>
          <div className="space-y-4">
            <div>
              <label className={LABEL}>Company</label>
              <select value={companyId} onChange={e => setCompanyId(Number(e.target.value))}
                disabled={companiesLoading} className={INPUT}>
                {companiesLoading && <option>Loading...</option>}
                {companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className={LABEL}>Job Role</label>
              <input type="text" value={jobRole} onChange={e => setJobRole(e.target.value)} className={INPUT} />
            </div>
            <div>
              <label className={LABEL}>Questions</label>
              <select value={totalQuestions} onChange={e => setTotalQuestions(Number(e.target.value))} className={INPUT}>
                {[5, 10, 15, 20].map(n => <option key={n} value={n}>{n} questions</option>)}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Template section */}
      {templates.length > 0 && (
        <div className="mb-6 border border-default rounded-lg p-3">
          <label className={LABEL}>Load Template</label>
          <select value={selectedTemplateId} onChange={e => handleTemplateChange(e.target.value)} className={INPUT}>
            <option value="">None (custom)</option>
            {templates.map(t => <option key={t.id} value={t.id}>{t.name} — {t.job_role}</option>)}
          </select>
        </div>
      )}

      {/* Save as template */}
      <div className="mb-6 border border-default rounded-lg p-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={saveAsTemplate} onChange={e => setSaveAsTemplate(e.target.checked)} className="rounded" />
          <Bookmark className="w-4 h-4 text-muted" />
          <span className="text-sm text-secondary">Save as template for this company</span>
        </label>
        {saveAsTemplate && (
          <input type="text" value={templateName} onChange={e => setTemplateName(e.target.value)}
            placeholder="Template name (e.g. Senior Engineer)" className={`mt-2 ${INPUT}`} />
        )}
      </div>

      {/* Start button */}
      <button onClick={handleStart} disabled={isStarting || !companyId}
        className="w-full py-3 bg-action-primary text-inverse rounded-xl font-semibold text-sm hover:bg-action-primary-hover active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md">
        {isStarting ? (
          <span className="inline-flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Starting Interview...
          </span>
        ) : 'Start Interview'}
      </button>
    </div>
  );
}
