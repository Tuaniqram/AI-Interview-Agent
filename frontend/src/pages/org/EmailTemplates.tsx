import { humanizeName } from '../../utils/humanize';
import { useEffect, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { Button } from '../../components/shared/Button';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { useToast } from '../../components/shared/Toast';
import { Eye, FileText, Pencil, Save } from 'lucide-react';

interface EmailTemplate {
  name: string;
  filename: string;
  path?: string;
}

const ORIGIN = typeof window !== 'undefined' ? window.location.origin : 'https://app.example.com';

const SAMPLE_VALUES: Record<string, string> = {
  APP_URL: ORIGIN,
  CANDIDATE_NAME: 'Amina Yusuf',
  INVITER_NAME: 'Daniel Mensah',
  ORG_NAME: 'GulfTex',
  JOB_ROLE: 'Backend Developer',
  ROLE: 'Member',
  INTERVIEW_MODE: 'Typing',
  DURATION: '30',
  EXPIRES_AT: '24 Nov 2026',
  SCHEDULED_AT: '24 Nov 2026, 10:00',
  HEADLINE: 'Good news',
  MESSAGE: 'the team has decided to move forward with you',
  STRENGTHS: 'Clear API design and strong SQL reasoning.',
  IMPROVEMENTS: 'Add more detail about failure handling.',
  VERIFY_URL: `${ORIGIN}/candidate/verify?token=sample-token`,
  RESET_URL: `${ORIGIN}/reset-password?token=sample-token`,
  CLAIM_URL: `${ORIGIN}/candidate/claim?token=sample-token`,
  ACCEPT_URL: `${ORIGIN}/invite/sample-token`,
  INVITE_URL: `${ORIGIN}/application-invite/sample-token`,
  REGISTER_URL: `${ORIGIN}/candidate/register`,
  DASHBOARD_URL: `${ORIGIN}/candidate/dashboard`,

  // Legacy lowercase templates (kept so older files preview too).
  candidate_name: 'Amina Yusuf',
  job_role: 'Backend Developer',
  org_name: 'GulfTex',
  interview_mode: 'Typing',
  duration: '30',
  interview_link: `${ORIGIN}/interview/sample-link`,
  expiry_hours: '72',
  strengths: 'Clear API design and strong SQL reasoning.',
  improvements: 'Add more detail about failure handling.',
  practice_link: `${ORIGIN}/candidate/practice`,
};

/** Fill ${PLACEHOLDER} / {{placeholder}} with sample values so the preview looks like a real email. */
function withSampleValues(content: string): string {
  return content.replace(/\$\{\s*([\w.]+)\s*\}|\{\{\s*([\w.]+)\s*\}\}/g, (_, braced: string, mustache: string) => {
    const key = braced ?? mustache;
    return SAMPLE_VALUES[key] ?? `Sample ${key.replace(/_/g, ' ').toLowerCase()}`;
  });
}

type Mode = 'edit' | 'preview';

const tabClass = (active: boolean) =>
  `inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-primary/40 ${
    active ? 'bg-action-primary/10 text-action-primary' : 'text-secondary hover:text-primary'
  }`;

export default function EmailTemplates() {
  const toast = useToast();
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<EmailTemplate | null>(null);
  const [content, setContent] = useState('');
  const [savedContent, setSavedContent] = useState('');
  const [mode, setMode] = useState<Mode>('edit');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLoading(true);
    apiClient.get<EmailTemplate[]>('/api/v1/admin/email-templates')
      .then(setTemplates)
      .catch(() => toast.error('Failed to load templates'))
      .finally(() => setLoading(false));
  }, []);

  const openTemplate = async (t: EmailTemplate) => {
    try {
      const data = await apiClient.get<EmailTemplate & { content: string }>(`/api/v1/admin/email-templates/${t.name}`);
      setSelected(data);
      setContent(data.content || '');
      setSavedContent(data.content || '');
      setMode('edit');
    } catch {
      toast.error('Failed to load template content');
    }
  };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const extension = selected.filename.match(/\.\w+$/)?.[0] ?? '.html';
      await apiClient.put(`/api/v1/admin/email-templates/${selected.name}`, { content, extension });
      setSavedContent(content);
      toast.success('Template saved');
    } catch {
      toast.error('Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <ContentSkeleton />;

  const dirty = !!selected && content !== savedContent;
  const isText = selected?.filename.endsWith('.txt');
  const preview = withSampleValues(content);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageHeader
        title="Email Templates"
        description="Edit and preview the emails the platform sends. Changes apply to every outgoing email."
      />

      {templates.length === 0 ? (
        <EmptyState title="No templates" description="Templates will appear here when the email folder is available." />
      ) : (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Choose an email template">
          {templates.map((t) => {
            const active = selected?.name === t.name;
            return (
              <button
                key={t.name}
                type="button"
                onClick={() => openTemplate(t)}
                aria-pressed={active}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-primary/40 ${
                  active
                    ? 'border-action-primary/30 bg-action-primary/10 text-action-primary'
                    : 'border-border bg-section text-secondary hover:border-action-primary/40 hover:text-primary'
                }`}
              >
                <FileText className="h-3.5 w-3.5" />
                {humanizeName(t.name)}
              </button>
            );
          })}
        </div>
      )}

      {selected ? (
        <Card padding="lg" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-primary">{humanizeName(selected.name)}</h2>
              <p className="mt-0.5 text-xs text-muted">
                {selected.filename}
                {dirty && <span className="ml-2 font-medium text-warning-text">Unsaved changes</span>}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex rounded-lg border border-border bg-page p-0.5" role="tablist" aria-label="Editor view">
                <button type="button" role="tab" aria-selected={mode === 'edit'} onClick={() => setMode('edit')} className={tabClass(mode === 'edit')}>
                  <Pencil className="h-3.5 w-3.5" /> Edit
                </button>
                <button type="button" role="tab" aria-selected={mode === 'preview'} onClick={() => setMode('preview')} className={tabClass(mode === 'preview')}>
                  <Eye className="h-3.5 w-3.5" /> Preview
                </button>
              </div>
              <Button size="sm" onClick={handleSave} loading={saving} disabled={!dirty}>
                <Save className="h-3.5 w-3.5 mr-1" /> Save changes
              </Button>
            </div>
          </div>

          {mode === 'edit' ? (
            <div>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                spellCheck={false}
                aria-label="Email template HTML"
                className="h-[62vh] min-h-[420px] w-full resize-y rounded-xl border border-border bg-page px-4 py-3 font-mono text-[13px] leading-relaxed text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-primary/30"
              />
              <p className="mt-2 text-[11px] text-muted">
                Placeholders are replaced with real values when the email is sent. Switch to Preview to see sample data.
              </p>
            </div>
          ) : (
            <div>
              {isText ? (
                <pre className="h-[62vh] min-h-[420px] overflow-auto whitespace-pre-wrap rounded-xl border border-border bg-page px-4 py-3 font-mono text-[13px] leading-relaxed text-primary">
                  {preview}
                </pre>
              ) : (
                <iframe
                  title="Email template preview"
                  srcDoc={preview}
                  sandbox=""
                  className="h-[62vh] min-h-[420px] w-full rounded-xl border border-border bg-white"
                />
              )}
              <p className="mt-2 text-[11px] text-muted">
                Preview uses sample values. Actual emails use the candidate's and organization's details.
              </p>
            </div>
          )}
        </Card>
      ) : (
        <EmptyState title="Select a template" description="Choose a template above to edit or preview it." />
      )}
    </div>
  );
}
