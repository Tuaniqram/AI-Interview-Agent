import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useOrg } from '../../contexts/OrgContext';
import { scorecardService } from '../../services/scorecardService';
import { PageHeader } from '../../components/shared/PageHeader';
import { Button } from '../../components/shared/Button';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Input } from '../../components/shared/Input';
import { Sheet, SheetSection } from '../../components/shared/Sheet';
import { CompetencyRows } from '../../components/org/CompetencyRows';
import { useToast } from '../../components/shared/Toast';
import { ClipboardList, Plus, Pencil, Trash2 } from 'lucide-react';
import type { ScorecardTemplate, CompetencyDef, ScorecardResultListItem } from '../../types/scorecard';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';

const DEFAULT_CATEGORIES = ['technical', 'communication', 'behavioral', 'leadership'];
const BLANK: CompetencyDef = { id: '', name: '', category: 'technical', weight: 1.0, max_score: 10.0 };

export default function Scorecards() {
  const { activeOrg } = useOrg();
  const toast = useToast();
  const [templates, setTemplates] = useState<ScorecardTemplate[]>([]);
  const [results, setResults] = useState<ScorecardResultListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ScorecardTemplate | null>(null);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState('');
  const [competencies, setCompetencies] = useState<CompetencyDef[]>([]);
  const [errors, setErrors] = useState<{ name?: string; rows?: string }>({});

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    Promise.all([
      scorecardService.list(activeOrg.id),
      scorecardService.listResults(activeOrg.id).catch(() => [] as ScorecardResultListItem[]),
    ])
      .then(([templateData, resultData]) => {
        setTemplates(templateData);
        setResults(resultData);
      })
      .catch(() => toast.error('Could not load scorecards. Reload the page to try again.'))
      .finally(() => setLoading(false));
  }, [activeOrg?.id]);

  const resetForm = () => {
    setName('');
    setCompetencies([{ ...BLANK }]);
    setErrors({});
    setShowForm(false);
    setEditingId(null);
  };

  const startNew = () => {
    resetForm();
    setShowForm(true);
  };

  const startEdit = (t: ScorecardTemplate) => {
    setName(t.name);
    setCompetencies(t.competencies.map(c => ({ ...c })));
    setErrors({});
    setEditingId(t.id);
    setShowForm(true);
  };

  const handleSave = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!activeOrg?.id) return;
    const found: typeof errors = {};
    if (!name.trim()) found.name = 'Give the scorecard a name.';
    if (!competencies.some(c => c.name.trim())) found.rows = 'Add at least one competency.';
    setErrors(found);
    if (Object.keys(found).length) return;

    setSaving(true);
    const payload = { name: name.trim(), competencies: competencies.filter(c => c.name.trim()) };
    try {
      if (editingId) {
        const updated = await scorecardService.update(activeOrg.id, editingId, payload);
        setTemplates(templates.map(t => t.id === editingId ? updated : t));
        toast.success('Scorecard saved');
      } else {
        const created = await scorecardService.create(activeOrg.id, payload);
        setTemplates([created, ...templates]);
        toast.success('Scorecard created');
      }
      resetForm();
    } catch {
      toast.error('Could not save the scorecard. Try again in a moment.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!activeOrg?.id) return;
    try {
      await scorecardService.delete(activeOrg.id, id);
      setTemplates(templates.filter(t => t.id !== id));
      toast.success('Scorecard deleted');
    } catch {
      toast.error('Could not delete the scorecard.');
    }
  };

  if (loading) return <ContentSkeleton />;

  return (
    <>
      <div className="space-y-8">
        <PageHeader
          title="Scorecards"
          description="The competencies an interview is scored on, and how much each one counts."
          actions={<Button icon={<Plus />} onClick={startNew}>New scorecard</Button>}
        />

        {templates.length === 0 ? (
          <div className="rounded-xl border border-border bg-section">
            <EmptyState
              icon={<ClipboardList />}
              title="No scorecards yet"
              description="Create one to choose which competencies count and how much. Without one, the built-in rubric is used."
              action={<Button icon={<Plus />} onClick={startNew}>New scorecard</Button>}
            />
          </div>
        ) : (
          <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden">
            {templates.map(t => (
              <li key={t.id} className="flex items-center gap-4 px-4 py-3 hover:bg-subtle transition-colors">
                <button type="button" onClick={() => startEdit(t)} className="flex-1 min-w-0 text-left rounded">
                  <span className="block text-sm font-medium text-primary truncate">{t.name}</span>
                  <span className="block text-xs text-tertiary truncate mt-0.5">
                    {t.competencies.map(c => `${c.name} ${c.weight}x`).join(' / ') || 'No competencies'}
                  </span>
                </button>
                <span className="text-xs text-secondary tabular whitespace-nowrap">
                  {t.competencies.length} {t.competencies.length === 1 ? 'competency' : 'competencies'}
                </span>
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

        <section className="space-y-3" aria-labelledby="results-heading">
          <div className="flex items-baseline justify-between">
            <h2 id="results-heading" className="text-sm font-semibold text-primary">Recent results</h2>
            <span className="text-xs text-tertiary tabular">
              {results.length} scored interview{results.length === 1 ? '' : 's'}
            </span>
          </div>
          {results.length === 0 ? (
            <div className="rounded-xl border border-border bg-section">
              <EmptyState title="No results yet" description="Weighted scorecard results appear here once a candidate finishes an interview." />
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-section overflow-x-auto">
              <table className="w-full text-[13px]">
                <thead className="bg-subtle text-xs text-tertiary border-b border-border">
                  <tr>
                    <th className="text-left font-medium px-4 py-2">Candidate</th>
                    <th className="text-left font-medium px-4 py-2">Role</th>
                    <th className="text-left font-medium px-4 py-2">Scorecard</th>
                    <th className="text-right font-medium px-4 py-2">Score</th>
                    <th className="px-4 py-2"><span className="sr-only">Report</span></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--divider)]">
                  {results.map(result => (
                    <tr key={result.id} className="hover:bg-subtle">
                      <td className="px-4 py-3">
                        <p className="font-medium text-primary">{result.candidate_name || 'Candidate'}</p>
                        {result.candidate_email && <p className="text-xs text-tertiary">{result.candidate_email}</p>}
                      </td>
                      <td className="px-4 py-3 text-secondary">{result.job_role || '—'}</td>
                      <td className="px-4 py-3 text-secondary">{result.template_name || 'Built-in'}</td>
                      <td className="px-4 py-3 text-right font-semibold text-primary tabular">
                        {result.weighted_score != null ? result.weighted_score.toFixed(2) : '—'}
                        <span className="text-xs text-tertiary font-normal"> / 10</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link to={`/interview/${result.session_id}/report`} className="text-xs font-medium text-action-primary hover:underline">
                          Report
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <Sheet
        open={showForm}
        onClose={resetForm}
        onSubmit={handleSave}
        width="lg"
        title={editingId ? 'Edit scorecard' : 'New scorecard'}
        description="The grading rubric. Templates can use a scorecard to decide what their interviews are scored on."
        footer={
          <>
            <Button type="button" variant="secondary" onClick={resetForm} disabled={saving}>Cancel</Button>
            <Button type="submit" loading={saving}>{editingId ? 'Save scorecard' : 'Create scorecard'}</Button>
          </>
        }
      >
        <SheetSection title="Basics">
          <Input
            label="Name"
            value={name}
            onChange={e => { setName(e.target.value); setErrors(p => ({ ...p, name: undefined })); }}
            placeholder="e.g. Software engineer scorecard"
            error={errors.name}
          />
        </SheetSection>
        <SheetSection title="Competencies" text="Weight is how much a competency counts toward the final score; top score is the most it can get.">
          <CompetencyRows
            rows={competencies}
            onChange={rows => { setCompetencies(rows); setErrors(p => ({ ...p, rows: undefined })); }}
            categories={DEFAULT_CATEGORIES}
            weight={{ min: 0, max: 5, step: 0.1 }}
            maxScore={{ min: 1, max: 100 }}
            blank={BLANK}
          />
          {errors.rows && <p className="text-xs text-error">{errors.rows}</p>}
        </SheetSection>
      </Sheet>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete scorecard?"
        message={`"${deleteTarget?.name}" will be deleted. This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => { if (deleteTarget) handleDelete(deleteTarget.id); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
