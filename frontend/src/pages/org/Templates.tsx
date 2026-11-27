import { useEffect, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { apiClient } from '../../services/apiClient';
import { orgContentService, type Template } from '../../services/orgContentService';
import { itService, type ItRole } from '../../services/itService';
import { PageHeader } from '../../components/shared/PageHeader';
import { Button } from '../../components/shared/Button';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Select } from '../../components/shared/Select';
import { Slider } from '../../components/shared/Slider';
import { Input, Textarea } from '../../components/shared/Input';
import { Sheet, SheetSection } from '../../components/shared/Sheet';
import { CompetencyRows } from '../../components/org/CompetencyRows';
import { scorecardService } from '../../services/scorecardService';
import type { ScorecardTemplate, CompetencyDef } from '../../types/scorecard';
import { useToast } from '../../components/shared/Toast';
import { FileStack, Pencil, Plus, Trash2 } from 'lucide-react';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';

interface OrgTemplate extends Template {
  it_role_id?: string | null;
  level_code?: string | null;
  description: string | null;
  interview_style: string | null;
  competencies: any[] | null;
}

type Source = 'defaults' | 'scorecard' | 'custom';

const COMPETENCY_CATEGORIES = ['technical', 'behavioral', 'cognitive', 'experience', 'general'];
const BLANK: CompetencyDef = { id: '', name: '', category: 'general', weight: 1.0, max_score: 10.0 };

const SOURCES: { value: Source; label: string; text: string }[] = [
  { value: 'defaults', label: 'Built-in', text: "AURA's standard competencies for the role. Right for most roles." },
  { value: 'scorecard', label: 'A scorecard', text: 'The competencies and weights of one of your scorecards.' },
  { value: 'custom', label: 'Custom', text: 'A list you write here, just for this template.' },
];

export default function Templates() {
  const { activeOrg } = useOrg();
  const toast = useToast();
  const [templates, setTemplates] = useState<OrgTemplate[]>([]);
  const [roles, setRoles] = useState<ItRole[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<OrgTemplate | null>(null);

  const [name, setName] = useState('');
  const [jobRole, setJobRole] = useState('');
  const [description, setDescription] = useState('');
  const [totalQuestions, setTotalQuestions] = useState(10);
  const [scorecardTemplateId, setScorecardTemplateId] = useState('');
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<{ name?: string; role?: string; scorecard?: string }>({});
  const [scorecards, setScorecards] = useState<ScorecardTemplate[]>([]);
  const [competencies, setCompetencies] = useState<CompetencyDef[]>([]);
  const [competencySource, setCompetencySource] = useState<Source>('defaults');

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    Promise.all([
      apiClient.get<OrgTemplate[]>(`/api/v1/orgs/${activeOrg.id}/templates`),
      itService.listRoles(),
      scorecardService.list(activeOrg.id).catch(() => []),
    ]).then(([t, r, sc]) => {
      setTemplates(t);
      setRoles(r);
      setScorecards(sc);
    }).catch(() => toast.error('Could not load templates. Reload the page to try again.'))
    .finally(() => setLoading(false));
  }, [activeOrg?.id]);

  const resetForm = () => {
    setName('');
    setJobRole('');
    setDescription('');
    setTotalQuestions(10);
    setScorecardTemplateId('');
    setCompetencies([]);
    setCompetencySource('defaults');
    setErrors({});
    setShowForm(false);
    setEditingId(null);
  };

  const startNew = () => {
    resetForm();
    setShowForm(true);
  };

  const startEdit = (t: OrgTemplate) => {
    setName(t.name);
    setJobRole(t.job_role);
    setDescription(t.description || '');
    setTotalQuestions(t.total_questions);
    setScorecardTemplateId(t.scorecard_template_id || '');
    setCompetencies((t.competencies || []).map(c => ({ ...c })));
    setCompetencySource(
      t.scorecard_template_id ? 'scorecard'
        : (t.competencies && t.competencies.length) ? 'custom'
        : 'defaults'
    );
    setErrors({});
    setEditingId(t.id);
    setShowForm(true);
  };

  const handleSave = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!activeOrg?.id) return;
    const found: typeof errors = {};
    if (!name.trim()) found.name = 'Give the template a name.';
    if (!jobRole.trim()) found.role = 'Choose the IT role it is for.';
    if (competencySource === 'scorecard' && !scorecardTemplateId) found.scorecard = 'Choose a scorecard, or pick another source.';
    setErrors(found);
    if (Object.keys(found).length) return;

    const orgId = activeOrg.id;
    setSaving(true);
    const cleaned = competencies.filter(c => c.name.trim());
    const payload = {
      name: name.trim(),
      job_role: jobRole.trim(),
      description: description.trim() || undefined,
      total_questions: totalQuestions,
      scorecard_template_id: competencySource === 'scorecard' ? (scorecardTemplateId || undefined) : undefined,
      competencies: competencySource === 'custom' ? (cleaned.length ? cleaned : undefined) : undefined,
    };
    try {
      if (editingId) {
        await orgContentService.updateTemplate(orgId, editingId, payload);
        toast.success('Template saved');
      } else {
        await orgContentService.createTemplate(orgId, payload);
        toast.success('Template created');
      }
      const updated = await apiClient.get<OrgTemplate[]>(`/api/v1/orgs/${orgId}/templates`);
      setTemplates(updated);
      resetForm();
    } catch {
      toast.error('Could not save the template. Try again in a moment.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (t: OrgTemplate) => {
    if (!activeOrg?.id) return;
    try {
      await orgContentService.deleteTemplate(activeOrg.id, t.id);
      setTemplates(templates.filter(tm => tm.id !== t.id));
      toast.success('Template deleted');
    } catch {
      toast.error('Could not delete the template.');
    }
  };

  if (loading) return <ContentSkeleton />;

  const filtered = selectedRole ? templates.filter(t => t.job_role === selectedRole) : templates;
  const scorecardName = (id?: string | null) => scorecards.find(s => s.id === id)?.name;
  const sourceOf = (t: OrgTemplate) =>
    t.scorecard_template_id ? `Scorecard: ${scorecardName(t.scorecard_template_id) ?? 'unknown'}`
      : t.competencies?.length ? `${t.competencies.length} custom competencies`
      : 'Built-in competencies';

  return (
    <>
      <div className="space-y-6">
        <PageHeader
          title="Templates"
          description="Reusable interview setups: the role, how many questions, and what the answers are scored on."
          actions={<Button icon={<Plus />} onClick={startNew}>New template</Button>}
        />

        {templates.length > 0 && (
          <div className="w-60">
            <Select
              value={selectedRole}
              onChange={setSelectedRole}
              placeholder="All IT roles"
              options={[{ value: '', label: 'All IT roles' }, ...roles.map(r => ({ value: r.name, label: r.name }))]}
            />
          </div>
        )}

        {filtered.length === 0 ? (
          <div className="rounded-xl border border-border bg-section">
            <EmptyState
              icon={<FileStack />}
              title={templates.length === 0 ? 'No templates yet' : 'No templates for this role'}
              description={templates.length === 0
                ? 'Create one so every interview for a role asks the same number of questions and is scored the same way.'
                : 'Pick another role, or create a template for this one.'}
              action={templates.length === 0 ? <Button icon={<Plus />} onClick={startNew}>New template</Button> : undefined}
            />
          </div>
        ) : (
          <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden">
            {filtered.map(t => (
              <li key={t.id} className="group flex items-center gap-4 px-4 py-3 hover:bg-subtle transition-colors">
                <button type="button" onClick={() => startEdit(t)} className="flex-1 min-w-0 text-left rounded">
                  <span className="block text-sm font-medium text-primary truncate">{t.name}</span>
                  <span className="block text-xs text-tertiary truncate mt-0.5">
                    {[t.job_role, t.level_code ? `${t.level_code} level` : null, sourceOf(t)].filter(Boolean).join(' / ')}
                  </span>
                  {t.description && <span className="block text-[13px] text-secondary truncate mt-0.5">{t.description}</span>}
                </button>
                <span className="text-xs text-secondary tabular whitespace-nowrap">{t.total_questions} questions</span>
                <span className="flex items-center gap-0.5">
                  <button onClick={() => startEdit(t)} className="p-1.5 rounded-md text-tertiary hover:text-primary hover:bg-hover" aria-label={`Edit ${t.name}`}>
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button onClick={() => setDeleteTarget(t)} className="p-1.5 rounded-md text-tertiary hover:text-error-text hover:bg-hover" aria-label={`Delete ${t.name}`}>
                    <Trash2 className="w-4 h-4" />
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <Sheet
        open={showForm}
        onClose={resetForm}
        onSubmit={handleSave}
        width="lg"
        title={editingId ? 'Edit template' : 'New template'}
        description="How an interview for this role runs: how many questions, and what the answers are scored on."
        footer={
          <>
            <Button type="button" variant="secondary" onClick={resetForm} disabled={saving}>Cancel</Button>
            <Button type="submit" loading={saving}>{editingId ? 'Save template' : 'Create template'}</Button>
          </>
        }
      >
        <SheetSection title="Basics">
          <Input label="Name" value={name} onChange={e => { setName(e.target.value); setErrors(p => ({ ...p, name: undefined })); }} placeholder="e.g. Senior frontend interview" error={errors.name} />
          <Select
            label="IT role"
            value={jobRole}
            onChange={v => { setJobRole(v); setErrors(p => ({ ...p, role: undefined })); }}
            placeholder="Choose a role"
            options={roles.map(r => ({ value: r.name, label: r.name }))}
            error={errors.role}
          />
          <div className="space-y-1.5">
            <span className="block text-[13px] font-medium text-primary">Questions</span>
            <Slider value={totalQuestions} onChange={setTotalQuestions} min={1} max={50} step={1} />
          </div>
          <Textarea label="Description" value={description} onChange={e => setDescription(e.target.value)} rows={3} placeholder="Optional. Who this template is for, for your team." />
        </SheetSection>

        <SheetSection title="Scored on" text="The competencies the answers are scored against.">
          <div role="radiogroup" aria-label="Competency source" className="grid gap-2 sm:grid-cols-3">
            {SOURCES.map(s => {
              const on = competencySource === s.value;
              return (
                <button
                  key={s.value}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => { setCompetencySource(s.value); setErrors(p => ({ ...p, scorecard: undefined })); }}
                  className={`text-left rounded-lg border px-3 py-2.5 transition-colors ${
                    on ? 'border-action-primary bg-action-primary-soft' : 'border-border hover:border-border-strong'
                  }`}
                >
                  <span className={`block text-[13px] font-medium ${on ? 'text-action-primary' : 'text-primary'}`}>{s.label}</span>
                  <span className="block text-xs text-secondary mt-0.5">{s.text}</span>
                </button>
              );
            })}
          </div>

          {competencySource === 'scorecard' && (
            scorecards.length === 0 ? (
              <p className="text-[13px] text-secondary">You have no scorecards yet. Create one on the Scorecards page, or pick another source.</p>
            ) : (
              <Select
                label="Scorecard"
                value={scorecardTemplateId}
                onChange={v => { setScorecardTemplateId(v); setErrors(p => ({ ...p, scorecard: undefined })); }}
                placeholder="Choose a scorecard"
                options={scorecards.map(sc => ({ value: sc.id, label: sc.name }))}
                error={errors.scorecard}
              />
            )
          )}

          {competencySource === 'custom' && (
            <CompetencyRows
              rows={competencies}
              onChange={setCompetencies}
              categories={COMPETENCY_CATEGORIES}
              weight={{ min: 0.5, max: 5, step: 0.5 }}
              blank={BLANK}
            />
          )}
        </SheetSection>
      </Sheet>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete template?"
        message={`"${deleteTarget?.name}" will be deleted. This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => { if (deleteTarget) handleDelete(deleteTarget); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
