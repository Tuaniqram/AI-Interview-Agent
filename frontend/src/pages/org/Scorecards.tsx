import { useEffect, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { scorecardService } from '../../services/scorecardService';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { Button } from '../../components/shared/Button';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { Select } from '../../components/shared/Select';
import { Slider } from '../../components/shared/Slider';
import { useToast } from '../../components/shared/Toast';
import { Plus, Pencil, Trash2, X } from 'lucide-react';
import type { ScorecardTemplate, CompetencyDef } from '../../types/scorecard';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';

const DEFAULT_CATEGORIES = ['technical', 'communication', 'behavioral', 'leadership'];
const FOCUS = 'focus:ring-2 focus:ring-[var(--focus-ring)] focus:outline-none focus:border-[var(--focus-ring)]';

export default function Scorecards() {
  const { activeOrg } = useOrg();
  const toast = useToast();
  const [templates, setTemplates] = useState<ScorecardTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState('');
  const [competencies, setCompetencies] = useState<CompetencyDef[]>([]);

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    scorecardService.list(activeOrg.id)
      .then(setTemplates)
      .catch(() => toast.error('Failed to load scorecards'))
      .finally(() => setLoading(false));
  }, [activeOrg?.id]);

  const resetForm = () => {
    setName('');
    setCompetencies([{ id: '', name: '', category: 'technical', weight: 1.0, max_score: 10.0 }]);
    setShowForm(false);
    setEditingId(null);
  };

  const startEdit = (t: ScorecardTemplate) => {
    setName(t.name);
    setCompetencies(t.competencies.map(c => ({ ...c })));
    setEditingId(t.id);
    setShowForm(true);
  };

  const addCompetency = () => {
    setCompetencies([...competencies, { id: '', name: '', category: 'technical', weight: 1.0, max_score: 10.0 }]);
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
    if (!activeOrg?.id || !name.trim()) return;
    setSaving(true);
    const payload = { name: name.trim(), competencies: competencies.filter(c => c.name.trim()) };
    try {
      if (editingId) {
        const updated = await scorecardService.update(activeOrg.id, editingId, payload);
        setTemplates(templates.map(t => t.id === editingId ? updated : t));
        toast.success('Scorecard updated');
      } else {
        const created = await scorecardService.create(activeOrg.id, payload);
        setTemplates([created, ...templates]);
        toast.success('Scorecard created');
      }
      resetForm();
    } catch {
      toast.error('Failed to save scorecard');
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
      toast.error('Failed to delete scorecard');
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <>
      <div className="space-y-6">
        <PageHeader title="Scorecards" description="Define custom evaluation scorecards for your interviews"
          actions={<Button onClick={() => { resetForm(); setShowForm(true); }}><Plus className="w-4 h-4 mr-1" /> New Scorecard</Button>}
        />

        {showForm && (
          <Card padding="lg" className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-primary">{editingId ? 'Edit Scorecard' : 'New Scorecard'}</h3>
              <button onClick={resetForm}><X className="w-4 h-4 text-muted" /></button>
            </div>
            <div>
              <label className="block text-sm font-medium text-primary mb-1">Name</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                className={`w-full px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border transition-colors ${FOCUS}`} placeholder="e.g. Software Engineer Scorecard" />
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-primary">Competencies</label>
                <Button type="button" size="sm" variant="secondary" onClick={addCompetency}>+ Add</Button>
              </div>
              {competencies.map((c, i) => (
                <div key={i} className="flex items-start gap-2 p-3 rounded-lg bg-page border border-border">
                  <div className="flex-1 space-y-2">
                    <div className="grid grid-cols-[1fr_auto] gap-2">
                      <input type="text" value={c.name} onChange={(e) => updateCompetency(i, 'name', e.target.value)}
                        className={`px-2 py-1.5 text-sm bg-input text-primary rounded border border-border transition-colors ${FOCUS}`} placeholder="Competency name" />
                      <Select value={c.category} onChange={v => updateCompetency(i, 'category', v)}
                        options={DEFAULT_CATEGORIES.map(cat => ({ value: cat, label: cat }))}
                      />
                    </div>
                    <Slider value={c.weight} onChange={(v) => updateCompetency(i, 'weight', v)} label="Weight" min={0} max={5} step={0.1} />
                    <Slider value={c.max_score} onChange={(v) => updateCompetency(i, 'max_score', v)} label="Max" min={1} max={100} step={1} />
                  </div>
                  <button onClick={() => removeCompetency(i)} className="mt-1"><X className="w-4 h-4 text-muted hover:text-error" /></button>
                </div>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={resetForm} disabled={saving}>Cancel</Button>
              <Button onClick={handleSave} loading={saving}>{editingId ? 'Update' : 'Create'}</Button>
            </div>
          </Card>
        )}

        {templates.length === 0 && !showForm ? (
          <EmptyState title="No scorecards yet" description="Create a scorecard to define custom evaluation criteria for your interviews" />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {templates.map(t => (
              <Card key={t.id} padding="lg" className="flex flex-col">
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-primary">{t.name}</h3>
                  <p className="text-xs text-muted mt-1">{t.competencies.length} competencies</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {t.competencies.slice(0, 4).map(c => (
                      <span key={c.id} className="text-[10px] px-2 py-0.5 rounded-full bg-action-primary/10 text-action-primary">
                        {c.name} ({c.weight}x)
                      </span>
                    ))}
                    {t.competencies.length > 4 && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-hover text-muted">+{t.competencies.length - 4}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 mt-3 pt-3 border-t border-border">
                  <button onClick={() => startEdit(t)} className="p-1.5 rounded hover:bg-hover text-muted hover:text-primary"><Pencil className="w-4 h-4" /></button>
                  <button onClick={() => setDeleteTarget(t.id)} className="p-1.5 rounded hover:bg-hover text-muted hover:text-error"><Trash2 className="w-4 h-4" /></button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Scorecard"
        message="Are you sure you want to delete this scorecard? This cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => { if (deleteTarget) handleDelete(deleteTarget); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
