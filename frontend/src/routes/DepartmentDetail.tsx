import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, FileText, ListChecks, ExternalLink, AlertCircle, Clock, Copy, Plus, Pencil, Trash2 } from 'lucide-react';
import { Breadcrumb } from '../components/shared/Breadcrumb';
import { departmentService, type Department, type Document, type SessionRecord } from '../services/departmentService';
import { marketplaceService } from '../services/marketplaceService';
import { useOrg } from '../contexts/OrgContext';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import { DateTimePicker } from '../components/shared/DateTimePicker';
import { MetricCard } from '../components/shared/MetricCard';
import { DocumentCard } from '../components/department/DocumentCard';
import { DocumentUploader } from '../components/department/DocumentUploader';
import { InterviewHistoryTable } from '../components/department/InterviewHistoryTable';
import { CardSkeleton } from '../components/shared/Skeleton';
import { ConfirmDialog } from '../components/shared/ConfirmDialog';
import { TagInput } from '../components/shared/TagInput';
import { useToast } from '../components/shared/Toast';
import type { OrgPublicListing } from '../types/marketplace';

type Tab = 'overview' | 'documents' | 'history' | 'listings';

export function DepartmentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('overview');
  const [department, setDepartment] = useState<Department | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [listings, setListings] = useState<OrgPublicListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { activeOrg } = useOrg();

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<OrgPublicListing | null>(null);
  const [fTitle, setFTitle] = useState('');
  const [fDescription, setFDescription] = useState('');
  const [fInterviewMode, setFInterviewMode] = useState('typing');
  const [fMaxCandidates, setFMaxCandidates] = useState('');
  const [fSkills, setFSkills] = useState('');
  const [fStartsAt, setFStartsAt] = useState('');
  const [fExpiresAt, setFExpiresAt] = useState('');
  const [saving, setSaving] = useState(false);
  const [formErrors, setFormErrors] = useState<{ title?: string; dates?: string }>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<OrgPublicListing | null>(null);
  const toast = useToast();

  const loadListings = useCallback(async () => {
    if (!activeOrg?.id || !id) return;
    try {
      const data = await marketplaceService.listOrgListings(activeOrg.id);
      setListings(data.filter(l => l.department_id === Number(id)));
    } catch {}
  }, [activeOrg?.id, id]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const d = await departmentService.getDepartment(Number(id));
        if (cancelled) return;
        setDepartment(d);
      } catch (err: any) {
        if (cancelled) return;
        if (err?.response?.status === 404) {
          navigate('/departments');
          return;
        }
        setError('Failed to load department details.');
        setLoading(false);
        return;
      }

      const docPromise = departmentService.listDocuments(Number(id))
        .then(data => { if (!cancelled) setDocuments(data); })
        .catch(() => {});

      const sessionPromise = departmentService.listSessions(Number(id))
        .then(data => { if (!cancelled) setSessions(data); })
        .catch(() => {});

      const listingPromise = activeOrg?.id
        ? marketplaceService.listOrgListings(activeOrg.id)
          .then(data => { if (!cancelled) setListings(data.filter(l => l.department_id === Number(id))); })
          .catch(() => {})
        : Promise.resolve();

      await Promise.allSettled([docPromise, sessionPromise, listingPromise]);
      if (!cancelled) setLoading(false);
    }

    load();
    return () => { cancelled = true; };
  }, [id, navigate, activeOrg?.id]);

  const resetForm = () => {
    setFTitle('');
    setFDescription('');
    setFInterviewMode('typing');
    setFMaxCandidates('');
    setFSkills('');
    setFStartsAt('');
    setFExpiresAt('');
    setEditing(null);
    setShowForm(false);
  };

  const handleEdit = (listing: OrgPublicListing) => {
    setEditing(listing);
    setFTitle(listing.title);
    setFDescription(listing.description || '');
    setFInterviewMode(listing.interview_mode);
    setFMaxCandidates(listing.max_candidates?.toString() || '');
    setFSkills(listing.skills_required || '');
    setFStartsAt(listing.starts_at ? listing.starts_at.slice(0, 16) : '');
    setFExpiresAt(listing.expires_at ? listing.expires_at.slice(0, 16) : '');
    setShowForm(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors: { title?: string; dates?: string } = {};
    if (!fTitle.trim()) errors.title = 'Title is required';
    if (fStartsAt && fExpiresAt && new Date(fStartsAt) >= new Date(fExpiresAt)) {
      errors.dates = 'Expiry must be after start date';
    }
    setFormErrors(errors);
    if (Object.keys(errors).length > 0 || !id) return;
    setSaving(true);
    try {
      if (editing) {
        await marketplaceService.updateListing(editing.id, {
          title: fTitle.trim(),
          department_id: Number(id),
          description: fDescription.trim() || undefined,
          interview_mode: fInterviewMode,
          max_candidates: fMaxCandidates ? parseInt(fMaxCandidates) : undefined,
          skills_required: fSkills.trim() || undefined,
          starts_at: fStartsAt ? new Date(fStartsAt).toISOString() : undefined,
          expires_at: fExpiresAt ? new Date(fExpiresAt).toISOString() : undefined,
        });
        toast.success('Listing updated');
      } else {
        await marketplaceService.createListing({
          title: fTitle.trim(),
          department_id: Number(id),
          description: fDescription.trim() || undefined,
          interview_mode: fInterviewMode,
          max_candidates: fMaxCandidates ? parseInt(fMaxCandidates) : undefined,
          skills_required: fSkills.trim() || undefined,
          starts_at: fStartsAt ? new Date(fStartsAt).toISOString() : undefined,
          expires_at: fExpiresAt ? new Date(fExpiresAt).toISOString() : undefined,
        });
        toast.success('Listing created');
      }
      resetForm();
      await loadListings();
    } catch (err) {
      toast.error('Failed to save listing');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (listing: OrgPublicListing) => {
    try {
      await marketplaceService.deleteListing(listing.id);
      toast.success(`"${listing.title}" deleted`);
      await loadListings();
    } catch (err) {
      toast.error('Failed to delete listing');
    }
  };

  const handleCopyLink = (token: string) => {
    const url = `${window.location.origin}/public-interview/${token}`;
    navigator.clipboard.writeText(url);
    setCopiedId(token);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'documents', label: `Documents (${documents.length})` },
    { key: 'listings', label: `Interview Listings (${listings.length})` },
    { key: 'history', label: `History (${sessions.length})` },
  ];

  const avgScore = sessions.length > 0
    ? sessions.reduce((a, b) => a + (b.final_score || 0), 0) / sessions.length
    : null;

  if (loading) {
    return (
      <div>
        <div className="h-8 w-32 mb-6"><CardSkeleton /></div>
        <CardSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <button onClick={() => navigate('/departments')} className="flex items-center gap-1.5 text-xs text-muted hover:text-secondary mb-4 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Departments
        </button>
        <Card>
          <div className="flex flex-col items-center py-8 text-center">
            <AlertCircle className="w-8 h-8 text-error mb-3" />
            <p className="text-sm text-primary font-medium mb-1">{error}</p>
            <button onClick={() => navigate('/departments')} className="mt-3 text-sm text-action-primary hover:text-action-primary-hover transition-colors">
              Back to Departments
            </button>
          </div>
        </Card>
      </div>
    );
  }

  if (!department) return null;

  return (
    <div>
      <Breadcrumb crumbs={[
        { label: 'Departments', to: '/departments' },
        { label: department?.name || 'Department' },
      ]} />

      <Card className="mb-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-action-primary/15 flex items-center justify-center shrink-0">
            <Building2 className="w-6 h-6 text-action-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-primary">{department.name}</h1>
            {department.website && <p className="text-sm text-muted mt-0.5">{department.website}</p>}
            {department.description && <p className="text-sm text-secondary mt-1 max-w-xl">{department.description}</p>}
          </div>
        </div>
      </Card>

      <div className="flex gap-4 mb-6">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-1 py-2 text-sm font-medium transition-colors relative ${
              tab === t.key
                ? 'text-action-primary'
                : 'text-secondary hover:text-primary'
            }`}
          >
            {t.label}
            {tab === t.key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-action-primary rounded-full" />
            )}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <MetricCard label="Total Sessions" value={sessions.length} icon={<ListChecks className="w-4 h-4" />} />
            <MetricCard label="Documents" value={documents.length} icon={<FileText className="w-4 h-4" />} />
            <MetricCard
              label="Avg Score"
              value={avgScore !== null ? avgScore.toFixed(1) : '—'}
              trend={avgScore !== null && avgScore >= 6 ? 'up' : avgScore !== null ? 'down' : undefined}
            />
          </div>
          <Card>
            <h3 className="text-sm font-medium text-primary mb-1">Department Info</h3>
            <p className="text-xs text-muted">Created {new Date(department.created_at).toLocaleDateString()}</p>
            {department.description && <p className="text-sm text-secondary mt-2">{department.description}</p>}
          </Card>
          {sessions.length > 0 && (
            <Card>
              <h3 className="text-sm font-medium text-primary mb-3">Recent Sessions</h3>
              <InterviewHistoryTable sessions={sessions.slice(0, 5)} />
            </Card>
          )}
        </div>
      )}

      {tab === 'documents' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <DocumentUploader departmentId={department.id} onUploaded={() => {
              departmentService.listDocuments(Number(id)).then(setDocuments);
            }} />
          </div>
          {documents.length === 0 ? (
            <Card>
              <p className="text-sm text-secondary py-8 text-center">No documents uploaded yet. Upload a PDF to add department knowledge.</p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {documents.map(d => (
                <DocumentCard key={d.id} document={d} onDelete={async (docId) => {
                  try {
                    await departmentService.deleteDocument(department.id, docId);
                    setDocuments(prev => prev.filter(x => x.id !== docId));
                  } catch {}
                }} />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'listings' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => { resetForm(); setShowForm(true); }}>
              <Plus className="w-4 h-4 mr-1.5" /> Create Interview Listing
            </Button>
          </div>

          <div className={`transition-all duration-300 ease-in-out overflow-hidden ${showForm ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'}`}>
            <form onSubmit={handleSave} className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-4 mb-4">
              <h3 className="font-semibold text-[var(--text-primary)]">
                {editing ? 'Edit Listing' : 'New Listing'} — {department?.name}
              </h3>

              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Title *</label>
                <input type="text" value={fTitle} onChange={e => { setFTitle(e.target.value); setFormErrors(prev => ({ ...prev, title: undefined })); }}
                  className={`w-full px-3 py-2 rounded-lg border bg-[var(--bg-page)] text-[var(--text-primary)] ${formErrors.title ? 'border-red-500' : 'border-[var(--border-color)]'}`} />
                {formErrors.title && <p className="text-xs text-error mt-1">{formErrors.title}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Description</label>
                <textarea value={fDescription} onChange={e => setFDescription(e.target.value)} rows={3}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Interview Mode</label>
                  <select value={fInterviewMode} onChange={e => setFInterviewMode(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]">
                    <option value="typing">Typing</option>
                    <option value="voice">Voice</option>
                    <option value="avatar">Avatar</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Max Candidates</label>
                  <input type="number" value={fMaxCandidates} onChange={e => setFMaxCandidates(e.target.value)} min={1}
                    placeholder="Unlimited"
                    className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
                </div>
              </div>

              <TagInput value={fSkills} onChange={setFSkills} label="Skills Required" placeholder="e.g. Python" />

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-secondary mb-1">Starts At</label>
                  <DateTimePicker value={fStartsAt} onChange={v => { setFStartsAt(v); setFormErrors(prev => ({ ...prev, dates: undefined })); }} placeholder="Pick start date & time" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-secondary mb-1">Expires At</label>
                  <DateTimePicker value={fExpiresAt} onChange={v => { setFExpiresAt(v); setFormErrors(prev => ({ ...prev, dates: undefined })); }} placeholder="Pick expiry date & time" />
                </div>
              </div>
              {formErrors.dates && <p className="text-xs text-error">{formErrors.dates}</p>}

              <div className="flex gap-3">
                <Button type="submit" loading={saving}>{editing ? 'Save Changes' : 'Create'}</Button>
                <Button type="button" variant="ghost" onClick={resetForm}>Cancel</Button>
              </div>
            </form>
          </div>

          {listings.length === 0 && !showForm ? (
            <Card>
              <div className="flex flex-col items-center py-8 text-center">
                <ExternalLink className="w-8 h-8 text-muted mb-3" />
                <p className="text-sm text-secondary">No interview listings for this department.</p>
              </div>
            </Card>
          ) : (
            <div className="space-y-3">
              {listings.map(listing => {
                const skills = listing.skills_required?.split(',').map(s => s.trim()).filter(Boolean) || [];
                const expired = listing.expires_at ? new Date(listing.expires_at) < new Date() : false;
                const expiryDays = listing.expires_at ? Math.ceil((new Date(listing.expires_at).getTime() - Date.now()) / 86400000) : null;
                return (
                  <Card key={listing.id}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <h3 className="font-semibold text-primary truncate">{listing.title}</h3>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${listing.is_open ? 'bg-green-500/15 text-green-500' : 'bg-red-500/15 text-red-500'}`}>
                            {listing.is_open ? 'Open' : 'Closed'}
                          </span>
                          {expired && listing.is_open && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/15 text-red-500">Expired</span>
                          )}
                          {expiryDays !== null && expiryDays > 0 && expiryDays <= 7 && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/15 text-yellow-500">
                              Expires in {expiryDays}d
                            </span>
                          )}
                        </div>
                        {listing.description && (
                          <p className="text-sm text-secondary line-clamp-2 mb-2">{listing.description}</p>
                        )}
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs px-2 py-0.5 rounded bg-action-primary/10 text-action-primary">
                            {listing.interview_mode}
                          </span>
                          {skills.map(s => (
                            <span key={s} className="text-xs px-2 py-0.5 rounded bg-page text-muted border border-border-color">
                              {s}
                            </span>
                          ))}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-muted mt-2">
                          {listing.starts_at && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Starts {new Date(listing.starts_at).toLocaleDateString()}</span>}
                          {listing.expires_at && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Expires {new Date(listing.expires_at).toLocaleDateString()}</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Button variant="ghost" size="sm" onClick={() => handleCopyLink(listing.token)} title="Copy link">
                          {copiedId === listing.token ? <span className="text-green-500">Copied!</span> : <Copy className="w-4 h-4" />}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(listing)} title="Edit">
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setDeleteTarget(listing)} title="Delete listing">
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {tab === 'history' && (
        <Card>
          <InterviewHistoryTable sessions={sessions} />
        </Card>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete Listing"
        message={`Are you sure you want to delete "${deleteTarget?.title}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => { if (deleteTarget) handleDelete(deleteTarget); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
