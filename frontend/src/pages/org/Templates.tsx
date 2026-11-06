import { useEffect, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { apiClient } from '../../services/apiClient';
import { departmentService, type Template } from '../../services/departmentService';
import { itService, type ItRole } from '../../services/itService';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { Button } from '../../components/shared/Button';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Select } from '../../components/shared/Select';
import { Slider } from '../../components/shared/Slider';
import { scorecardService } from '../../services/scorecardService';
import type { ScorecardTemplate, CompetencyDef } from '../../types/scorecard';
import { useToast } from '../../components/shared/Toast';
import { Plus, Pencil, Trash2, X } from 'lucide-react';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';

interface OrgTemplate extends Template {
  department_name: string;
  it_role_id?: string | null;
  level_code?: string | null;
  description: string | null;
  interview_style: string | null;
  competencies: any[] | null;
}

const COMPETENCY_CATEGORIES = ['technical', 'behavioral', 'cognitive', 'experience', 'general'];
const FOCUS = 'focus:ring-2 focus:ring-[var(--focus-ring)] focus:outline-none focus:border-[var(--focus-ring)]';
const DEFAULT_DEPARTMENT_ID = 0;

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
  const [scorecards, setScorecards] = useState<ScorecardTemplate[]>([]);
  const [competencies, setCompetencies] = useState<CompetencyDef[]>([]);
  const [competencySource, setCompetencySource] = useState<'defaults' | 'scorecard' | 'custom'>('defaults');

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
    }).catch(() => toast.error('Failed to load templates'))
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
    setShowForm(false);
    setEditingId(null);
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
    setEditingId(t.id);
    setShowForm(true);
  };

  const addCompetency = () => {
    setCompetencies([...competencies, { id: '', name: '', category: 'general', weight: 1.0, max_score: 10.0 }]);
  };

  const updateCompetency = (i: number, field: keyof CompetencyDef, value: any) => {
    const updated = competencies.map((c, idx) => idx === i ? { ...c, [field]: value } : c);
    if (field === 'name' && !competencies[i].id) {
      updated[i] = { ...updated[i], id: value.toLowerCase().replace(/\s+/g, '_') };
    }
    setCompetencies(updated);
  };

  const removeCompetency = (i: number) => {
    setCompetencies(competencies.filter((_, idx) => idx !== i));
  };

  const handleSave = async () => {
    if (!activeOrg?.id || !name.trim() || !jobRole.trim()) return;
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
        await departmentService.updateTemplate(DEFAULT_DEPARTMENT_ID, editingId, payload);
        toast.success('Template updated');
      } else {
        await departmentService.createTemplate(DEFAULT_DEPARTMENT_ID, payload);
        toast.success('Template created');
      }
      const updated = await apiClient.get<OrgTemplate[]>(`/api/v1/orgs/${activeOrg.id}/templates`);
      setTemplates(updated);
      resetForm();
    } catch {
      toast.error('Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (t: OrgTemplate) => {
    try {
      await departmentService.deleteTemplate(t.department_id, t.id);
      setTemplates(templates.filter(tm => tm.id !== t.id));
      toast.success('Template deleted');
    } catch {
      toast.error('Failed to delete template');
    }
  };

  const confirmDelete = (t: OrgTemplate) => {
    setDeleteTarget(t);
  };

  if (loading) return <ContentSkeleton />;

  const filtered = selectedRole ? templates.filter(t => t.job_role === selectedRole) : templates;

  return (
    <>
      <div className="space-y-6">
        <PageHeader title="Templates Library" description="Interview templates across all IT roles"
          actions={<Button onClick={() => { resetForm(); setShowForm(true); }}><Plus className="w-4 h-4 mr-1" /> New Template</Button>}
        />

        <div className="flex items-center gap-3">
          <Select
            value={selectedRole}
            onChange={setSelectedRole}
            placeholder="All IT roles"
            options={roles.map(r => ({ value: r.name, label: r.name }))}
          />
        </div>

        {showForm && (
          <Card padding="lg" className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-primary">{editingId ? 'Edit Template' : 'New Template'}</h3>
              <button onClick={resetForm}><X className="w-4 h-4 text-muted" /></button>
            </div>
            <div className="rounded-lg bg-page border border-border px-3 py-2.5 text-xs text-secondary space-y-1">
              <p className="text-primary font-medium">Not sure what to fill in?</p>
              <p>An <span className="text-primary font-medium">interview template</span> defines how the interview runs: which IT role, level, and how many questions.</p>
              <p><span className="text-primary font-medium">Competencies</span> are the skill list AURA evaluates against — you pick the source below. Not sure? AURA defaults works for most roles.</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Template Name</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                  className={`w-full px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border transition-colors ${FOCUS}`} placeholder="e.g. Senior Frontend Interview" />
              </div>
              <div>
                <label className="block text-sm font-medium text-primary mb-1">IT Role</label>
                <Select
                  value={jobRole}
                  onChange={setJobRole}
                  placeholder="Select IT role"
                  options={roles.map(r => ({ value: r.name, label: r.name }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Total Questions</label>
                <Slider value={totalQuestions} onChange={setTotalQuestions} min={1} max={50} step={1} />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-primary mb-1">Description</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
                className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border" placeholder="Template description..." />
            </div>
            <div className="space-y-3">
              <label className="block text-sm font-medium text-primary">Competencies — what AURA evaluates</label>
              <div className="flex gap-2">
                {([
                  { value: 'defaults', label: 'AURA defaults' },
                  { value: 'scorecard', label: 'Scorecard' },
                  { value: 'custom', label: 'Custom' },
                ] as const).map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setCompetencySource(opt.value)}
                    className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                      competencySource === opt.value
                        ? 'bg-action-primary text-inverse border-transparent'
                        : 'bg-input text-secondary border-border hover:bg-hover'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>

              {competencySource === 'scorecard' && (
                <div>
                  <Select
                    label="Scorecard"
                    value={scorecardTemplateId}
                    onChange={setScorecardTemplateId}
                    placeholder="Select a scorecard"
                    options={scorecards.map(sc => ({ value: sc.id, label: sc.name }))}
                  />
                  <p className="text-xs text-muted mt-1">The scorecard's competencies and weights will drive the interview.</p>
                </div>
              )}

              {competencySource === 'custom' && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-medium text-primary">Competencies</label>
                    <button type="button" onClick={addCompetency}
                      className="inline-flex items-center gap-1 text-xs text-action-primary hover:text-primary">
                      <Plus className="w-3.5 h-3.5" /> Add competency
                    </button>
                  </div>
                  <p className="text-xs text-muted">These competencies will drive interviews using this template.</p>
                  <div className="space-y-2">
                    {competencies.map((c, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <input type="text" value={c.name} onChange={(e) => updateCompetency(i, 'name', e.target.value)}
                          className={`flex-1 px-3 py-1.5 text-sm bg-input text-primary rounded-lg border border-border ${FOCUS}`}
                          placeholder="Competency name (e.g. Marketing Strategy)" />
                        <Select
                          value={c.category}
                          onChange={v => updateCompetency(i, 'category', v)}
                          options={COMPETENCY_CATEGORIES.map(cat => ({ value: cat, label: cat }))}
                          className="w-36"
                        />
                        <input type="number" min={0.5} max={5} step={0.5} value={c.weight}
                          onChange={(e) => updateCompetency(i, 'weight', Number(e.target.value))}
                          className="w-20 px-3 py-1.5 text-sm bg-input text-primary rounded-lg border border-border" title="Weight" />
                        <button type="button" onClick={() => removeCompetency(i)}
                          className="p-1.5 rounded hover:bg-hover text-muted hover:text-error"><X className="w-4 h-4" /></button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {competencySource === 'defaults' && (
                <p className="text-xs text-secondary">Uses AURA's built-in competency set — good for most roles.</p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={resetForm} disabled={saving}>Cancel</Button>
              <Button onClick={handleSave} loading={saving}>{editingId ? 'Update' : 'Create'}</Button>
            </div>
          </Card>
        )}

        {filtered.length === 0 && !showForm ? (
          <EmptyState title="No templates yet" description="Create interview templates to standardize your hiring process" />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map(t => (
              <Card key={t.id} padding="lg" className="flex flex-col">
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-primary">{t.name}</h3>
                      <p className="text-xs text-action-primary mt-0.5">{t.job_role}</p>
                    </div>
                  </div>
                  <p className="text-xs text-muted mt-2">{t.level_code ? `${t.level_code} level` : 'IT role'}</p>
                  {t.description && <p className="text-xs text-secondary mt-1 line-clamp-2">{t.description}</p>}
                  <div className="flex items-center gap-2 mt-3">
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-action-primary/10 text-action-primary">AURA</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-hover text-muted">{t.total_questions} questions</span>
                    {t.competencies && t.competencies.length > 0 && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-hover text-muted">{t.competencies.length} competencies</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 mt-3 pt-3 border-t border-border">
                  <button onClick={() => startEdit(t)} className="p-1.5 rounded hover:bg-hover text-muted hover:text-primary"><Pencil className="w-4 h-4" /></button>
                  <button onClick={() => confirmDelete(t)} className="p-1.5 rounded hover:bg-hover text-muted hover:text-error"><Trash2 className="w-4 h-4" /></button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Template"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => { if (deleteTarget) handleDelete(deleteTarget); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
