import { useEffect, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { apiClient } from '../../services/apiClient';
import { departmentService, type Template } from '../../services/departmentService';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { Button } from '../../components/shared/Button';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { useToast } from '../../components/shared/Toast';
import { Plus, Pencil, Trash2, X } from 'lucide-react';
import { ConfirmDialog } from '../../components/shared/ConfirmDialog';

interface OrgTemplate extends Template {
  department_name: string;
  description: string | null;
  interview_style: string | null;
  competencies: any[] | null;
}

const INTERVIEW_STYLES = ['STANDARD', 'CONVERSATIONAL', 'TECHNICAL_DEEP', 'BEHAVIORAL', 'CASE_STUDY'];

export default function Templates() {
  const { activeOrg } = useOrg();
  const toast = useToast();
  const [templates, setTemplates] = useState<OrgTemplate[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [selectedDept, setSelectedDept] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<OrgTemplate | null>(null);

  const [name, setName] = useState('');
  const [jobRole, setJobRole] = useState('');
  const [description, setDescription] = useState('');
  const [interviewStyle, setInterviewStyle] = useState('STANDARD');
  const [totalQuestions, setTotalQuestions] = useState(10);
  const [deptId, setDeptId] = useState<number | ''>('');

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    Promise.all([
      apiClient.get<OrgTemplate[]>(`/api/v1/orgs/${activeOrg.id}/templates`),
      apiClient.get<any[]>('/api/v1/departments'),
    ]).then(([t, d]) => {
      setTemplates(t);
      setDepartments(d);
    }).catch(() => toast.error('Failed to load templates'))
    .finally(() => setLoading(false));
  }, [activeOrg?.id]);

  const resetForm = () => {
    setName('');
    setJobRole('');
    setDescription('');
    setInterviewStyle('STANDARD');
    setTotalQuestions(10);
    setDeptId('');
    setShowForm(false);
    setEditingId(null);
  };

  const startEdit = (t: OrgTemplate) => {
    setName(t.name);
    setJobRole(t.job_role);
    setDescription(t.description || '');
    setInterviewStyle(t.interview_style || 'STANDARD');
    setTotalQuestions(t.total_questions);
    setDeptId(t.department_id);
    setEditingId(t.id);
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!activeOrg?.id || !name.trim() || !jobRole.trim() || deptId === '') return;
    const payload = {
      name: name.trim(),
      job_role: jobRole.trim(),
      description: description.trim() || undefined,
      interview_style: interviewStyle,
      total_questions: totalQuestions,
    };
    try {
      if (editingId) {
        await departmentService.updateTemplate(deptId as number, editingId, payload);
        toast.success('Template updated');
      } else {
        await departmentService.createTemplate(deptId as number, payload);
        toast.success('Template created');
      }
      const updated = await apiClient.get<OrgTemplate[]>(`/api/v1/orgs/${activeOrg.id}/templates`);
      setTemplates(updated);
      resetForm();
    } catch {
      toast.error('Failed to save template');
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

  if (loading) return <LoadingSpinner />;

  const filtered = selectedDept ? templates.filter(t => t.department_id === Number(selectedDept)) : templates;

  return (
    <>
      <div className="space-y-6">
        <PageHeader title="Templates Library" description="Interview templates across all departments"
          actions={<Button onClick={() => { resetForm(); setShowForm(true); }}><Plus className="w-4 h-4 mr-1" /> New Template</Button>}
        />

        <div className="flex items-center gap-3">
          <select value={selectedDept} onChange={(e) => setSelectedDept(e.target.value)}
            className="px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border">
            <option value="">All Departments</option>
            {departments.map(d => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>

        {showForm && (
          <Card padding="lg" className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-primary">{editingId ? 'Edit Template' : 'New Template'}</h3>
              <button onClick={resetForm}><X className="w-4 h-4 text-muted" /></button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Template Name</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border" placeholder="e.g. Senior Frontend Interview" />
              </div>
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Job Role</label>
                <input type="text" value={jobRole} onChange={(e) => setJobRole(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border" placeholder="e.g. Software Engineer" />
              </div>
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Department</label>
                <select value={deptId} onChange={(e) => setDeptId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border">
                  <option value="">Select department</option>
                  {departments.map(d => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Interview Style</label>
                <select value={interviewStyle} onChange={(e) => setInterviewStyle(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border">
                  {INTERVIEW_STYLES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-primary mb-1">Total Questions</label>
                <input type="number" value={totalQuestions} onChange={(e) => setTotalQuestions(parseInt(e.target.value) || 10)}
                  className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border" min="1" max="50" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-primary mb-1">Description</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
                className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border" placeholder="Template description..." />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={resetForm}>Cancel</Button>
              <Button onClick={handleSave}>{editingId ? 'Update' : 'Create'}</Button>
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
                  <p className="text-xs text-muted mt-2">{t.department_name}</p>
                  {t.description && <p className="text-xs text-secondary mt-1 line-clamp-2">{t.description}</p>}
                  <div className="flex items-center gap-2 mt-3">
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-action-primary/10 text-action-primary">{t.interview_style || 'STANDARD'}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-hover text-muted">{t.total_questions} questions</span>
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
