import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Bookmark, MessageSquare, Mic, Video, ChevronDown, Check } from 'lucide-react';
import { Card } from '../components/shared/Card';
import { PageHeader } from '../components/shared/PageHeader';
import { departmentService, type Department, type Template } from '../services/departmentService';
import { useInterviewStore } from '../state/interviewStore';
import { useToast } from '../components/shared/Toast';

const INPUT = 'w-full px-3 py-1.5 text-sm bg-input text-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] transition-colors';
const SELECT = INPUT + ' appearance-none';
const LABEL = 'block text-xs font-medium text-secondary mb-1';

export function NewInterview() {
  const navigate = useNavigate();
  const { actions } = useInterviewStore();
  const [selectedMode, setSelectedMode] = React.useState('avatar');
  const [departmentId, setCompanyId] = React.useState<number>(0);
  const [jobRole, setJobRole] = React.useState('Software Engineer');
  const [totalQuestions, setTotalQuestions] = React.useState(10);

  const [isStarting, setIsStarting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [companies, setCompanies] = React.useState<Department[]>([]);
  const [companiesLoading, setCompaniesLoading] = React.useState(true);
  const toast = useToast();

  const [templates, setTemplates] = React.useState<Template[]>([]);
  const [templatesLoading, setTemplatesLoading] = React.useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = React.useState<string>('');
  const [saveAsTemplate, setSaveAsTemplate] = React.useState(false);
  const [templateName, setTemplateName] = React.useState('');

  React.useEffect(() => {
    setCompaniesLoading(true);
    departmentService.listDepartments()
      .then(data => {
        setCompanies(data);
        if (data.length > 0) setCompanyId(data[0].id);
      })
      .catch(() => {})
      .finally(() => setCompaniesLoading(false));
  }, []);

  React.useEffect(() => {
    if (!departmentId) {
      setTemplates([]);
      setSelectedTemplateId('');
      return;
    }
    setTemplatesLoading(true);
    setSelectedTemplateId('');
    departmentService.listTemplates(departmentId)
      .then(setTemplates)
      .catch(() => setTemplates([]))
      .finally(() => setTemplatesLoading(false));
  }, [departmentId]);

  const selectedTemplate = React.useMemo(
    () => templates.find(t => t.id === selectedTemplateId),
    [templates, selectedTemplateId]
  );

  const handleTemplateChange = (templateId: string) => {
    setSelectedTemplateId(templateId);
    const t = templates.find(tmp => tmp.id === templateId);
    if (t) {
      setCompanyId(t.department_id);
      setJobRole(t.job_role);
      setTotalQuestions(t.total_questions);
      setSelectedMode('avatar');
    }
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) return;
    try {
      await departmentService.createTemplate(departmentId, {
        name: templateName.trim(),
        job_role: jobRole,
        total_questions: totalQuestions,
      });
      toast.success('Template saved');
      setSaveAsTemplate(false);
      setTemplateName('');
      const data = await departmentService.listTemplates(departmentId);
      setTemplates(data);
    } catch {
      toast.error('Failed to save template');
    }
  };

  const handleStart = async () => {
    setIsStarting(true);
    setError(null);
    try {
      await actions.startInterview({
        departmentId,
        jobRole,
        totalQuestions,
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
    <div className="max-w-4xl">
      <PageHeader title="New Interview" description="Configure your AI interview session" />

      {error && (
        <Card className="mb-6 bg-error-bg" padding="sm">
          <p className="text-sm text-error-text">{error}</p>
        </Card>
      )}

      <Card className="mb-6">
        <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-3">Interview Mode</h3>
        <div className="grid grid-cols-3 gap-3">
          {modes.map(m => {
            const Icon = m.icon;
            const active = selectedMode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setSelectedMode(m.id)}
                className={`p-4 rounded-xl text-left transition-all ${
                  active
                    ? 'bg-input ring-2 ring-action-primary/20'
                    : 'bg-input hover:bg-hover'
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
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <Card className="lg:col-span-2" padding="md">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-3">Interview Config</h3>
              <div className="space-y-3">
                <div>
                  <label className={LABEL}>Department</label>
                  <div className="relative">
                    <select value={departmentId} onChange={e => setCompanyId(Number(e.target.value))}
                      disabled={companiesLoading} className={SELECT + ' pr-8'}>
                      {companiesLoading && <option>Loading...</option>}
                      {companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted pointer-events-none" />
                  </div>
                </div>
                <div>
                  <label className={LABEL}>Job Role</label>
                  <input type="text" value={jobRole} onChange={e => setJobRole(e.target.value)} className={INPUT} />
                </div>
                <div>
                  <label className={LABEL}>Questions</label>
                  <div className="relative">
                    <select value={totalQuestions} onChange={e => setTotalQuestions(Number(e.target.value))} className={SELECT + ' pr-8'}>
                      {[5, 10, 15, 20].map(n => <option key={n} value={n}>{n} questions</option>)}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted pointer-events-none" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Card>

        <Card padding="md" className="min-h-[210px] flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">Templates</h3>
            {templatesLoading && <Loader2 className="w-3 h-3 animate-spin text-muted" />}
          </div>

          <div className="flex-1">
            {templates.length > 0 ? (
              <div>
                <div className="relative">
                  <select value={selectedTemplateId} onChange={e => handleTemplateChange(e.target.value)}
                    className={SELECT + ' pr-8 text-xs'}>
                    <option value="">Custom setup</option>
                    {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                  </select>
                  <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted pointer-events-none" />
                </div>

                {selectedTemplate && (
                  <div className="mt-2 p-2.5 bg-input rounded-lg space-y-1">
                    <p className="text-xs font-medium text-primary">{selectedTemplate.name}</p>
                    <div className="flex items-center gap-2 text-[10px] text-muted">
                      <span>{selectedTemplate.job_role}</span>
                      <span>·</span>
                      <span>{selectedTemplate.total_questions} Q</span>
                    </div>
                    <p className="text-[10px] text-success-text flex items-center gap-1">
                      <Check className="w-2.5 h-2.5" /> Applied
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col justify-center min-h-[60px]">
                <p className="text-xs text-muted">
                  {templatesLoading
                    ? 'Loading...'
                    : departmentId
                      ? 'No templates saved for this department.'
                      : 'Select a company first.'}
                </p>
                {!templatesLoading && departmentId && (
                  <p className="text-[10px] text-muted mt-1">
                    Configure and use "Save as template" below.
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="mt-3 pt-3 border-t border-border">
            {saveAsTemplate ? (
              <div className="flex items-center gap-2">
                <input type="text" value={templateName} onChange={e => setTemplateName(e.target.value)}
                  placeholder="Name this template..." aria-label="Template name"
                  className="flex-1 min-w-0 px-2.5 py-1.5 text-xs bg-input text-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] transition-colors placeholder:text-muted" />
                <button onClick={handleSaveTemplate} disabled={!templateName.trim()}
                  className="px-3 py-1.5 text-xs bg-action-primary text-inverse rounded-lg font-medium hover:bg-action-primary-hover disabled:opacity-40 disabled:cursor-not-allowed transition-all shrink-0">
                  Save
                </button>
                <button onClick={() => setSaveAsTemplate(false)}
                  className="px-2 py-1.5 text-xs text-muted hover:text-secondary transition-colors shrink-0">
                  Cancel
                </button>
              </div>
            ) : (
              <button onClick={() => setSaveAsTemplate(true)}
                className="flex items-center gap-1.5 text-xs text-muted hover:text-secondary transition-colors">
                <Bookmark className="w-3.5 h-3.5" />
                Save as template
              </button>
            )}
          </div>
        </Card>
      </div>

      <div className="flex items-center justify-end">
        <button onClick={handleStart} disabled={isStarting || !departmentId}
          className="px-8 py-2.5 bg-action-primary text-inverse rounded-lg font-semibold text-sm hover:bg-action-primary-hover active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md">
          {isStarting ? (
            <span className="inline-flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Starting...
            </span>
          ) : 'Start Interview'}
        </button>
      </div>
    </div>
  );
}
