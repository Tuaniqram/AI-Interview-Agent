import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Bookmark } from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { useInterviewStore } from '../state/interviewStore';
import { Card } from '../components/shared/Card';

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

  // Template state
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

  // Load templates when company changes
  React.useEffect(() => {
    if (!companyId) return;
    apiClient.get<Template[]>(`/templates/?company_id=${companyId}`)
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, [companyId]);

  // Apply template
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
      // Save as template if requested
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

        {/* Load Template */}
        {templates.length > 0 && (
          <div className="mb-6">
            <label className="block text-xs font-medium text-secondary mb-1.5">Load Template</label>
            <select value={selectedTemplateId} onChange={e => handleTemplateChange(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus">
              <option value="">None (custom)</option>
              {templates.map(t => <option key={t.id} value={t.id}>{t.name} — {t.job_role}</option>)}
            </select>
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
            <label className="block text-xs font-medium text-secondary mb-1.5">Candidate Name</label>
            <input type="text" value={candidateName} onChange={e => setCandidateName(e.target.value)} placeholder="e.g. John Doe"
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus" />
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Candidate Email</label>
            <input type="email" value={candidateEmail} onChange={e => setCandidateEmail(e.target.value)} placeholder="e.g. john@example.com"
              className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus" />
          </div>
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

        {/* Save as Template */}
        <div className="mb-6 border border-default rounded-lg p-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={saveAsTemplate} onChange={e => setSaveAsTemplate(e.target.checked)} className="rounded" />
            <Bookmark className="w-4 h-4 text-muted" />
            <span className="text-sm text-secondary">Save as template for this company</span>
          </label>
          {saveAsTemplate && (
            <input type="text" value={templateName} onChange={e => setTemplateName(e.target.value)}
              placeholder="Template name (e.g. Senior Engineer)"
              className="mt-2 w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus" />
          )}
        </div>

        <button onClick={handleStart} disabled={isStarting || !companyId}
          className="w-full py-3 bg-action-primary text-inverse rounded-xl font-semibold text-sm hover:bg-action-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md">
          {isStarting ? <><Loader2 className="animate-spin w-4 h-4 inline mr-2" />Starting...</> : 'Start Interview'}
        </button>
      </Card>
    </div>
  );
}
