import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ExternalLink, AlertCircle, Check, Copy, Plus, Pencil, Trash2 } from 'lucide-react';
import { orgContentService, type Document, type SessionRecord, type Template } from '../services/orgContentService';
import { marketplaceService } from '../services/marketplaceService';
import { itService, type ItRole } from '../services/itService';
import { useOrg } from '../contexts/OrgContext';
import { Button } from '../components/shared/Button';
import { Card } from '../components/shared/Card';
import { DateTimePicker } from '../components/shared/DateTimePicker';
import { StatStrip } from '../components/shared/StatStrip';
import { DocumentCard } from '../components/org/DocumentCard';
import { DocumentUploader } from '../components/org/DocumentUploader';
import { InterviewHistoryTable } from '../components/org/InterviewHistoryTable';
import { CardSkeleton } from '../components/shared/Skeleton';
import { ConfirmDialog } from '../components/shared/ConfirmDialog';
import { TagInput } from '../components/shared/TagInput';
import { Select } from '../components/shared/Select';
import { Input, Textarea } from '../components/shared/Input';
import { Sheet, SheetSection } from '../components/shared/Sheet';
import { EmptyState } from '../components/shared/EmptyState';
import { useToast } from '../components/shared/Toast';
import type { OrgPublicListing } from '../types/marketplace';

const INTERVIEW_STYLES = [
  { value: 'STANDARD', label: 'Standard', desc: 'Balanced across all competencies' },
  { value: 'FRESH_GRAD', label: 'Fresh Grad', desc: 'Entry-level, core + DSA + learning, mentor persona' },
  { value: 'JUNIOR', label: 'Junior', desc: '1-3yr exp, framework + teamwork, friendly persona' },
  { value: 'MID_LEVEL', label: 'Mid-Level', desc: '3-5yr exp, system design + ownership' },
  { value: 'SENIOR', label: 'Senior', desc: '5-8yr exp, architecture + leadership, formal persona' },
  { value: 'TECH_LEAD', label: 'Tech Lead', desc: 'Lead/Staff, leadership + people' },
  { value: 'EM', label: 'Engineering Manager', desc: 'Process + strategy' },
  { value: 'FAANG', label: 'FAANG', desc: 'Algorithm-heavy, deep probes' },
  { value: 'FAANG_LITE', label: 'FAANG Lite', desc: 'FAANG approach cost-optimized' },
  { value: 'STARTUP', label: 'Startup', desc: 'Full-stack, adaptability, speed' },
  { value: 'CONTRACT', label: 'Contract', desc: 'Domain depth, delivery, independence' },
  { value: 'EXECUTIVE', label: 'Executive', desc: 'C-level, strategy + vision' },
  { value: 'STRESS_TEST', label: 'Stress Test', desc: 'Resilience under pressure' },
];

type Tab = 'overview' | 'documents' | 'history' | 'listings';

const fmtDate = (d: string) => new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });

export function Company() {
  const navigate = useNavigate();
  const { activeOrg } = useOrg();
  const [tab, setTab] = useState<Tab>('overview');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [listings, setListings] = useState<OrgPublicListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<OrgPublicListing | null>(null);
  const [fTitle, setFTitle] = useState('');
  const [fRoleId, setFRoleId] = useState('');
  const [fDescription, setFDescription] = useState('');
  const [fMaxCandidates, setFMaxCandidates] = useState('');
  const [fSkills, setFSkills] = useState('');
  const [fStyle, setFStyle] = useState('STANDARD');
  const [fStartsAt, setFStartsAt] = useState('');
  const [fExpiresAt, setFExpiresAt] = useState('');
  const [saving, setSaving] = useState(false);
  const [formErrors, setFormErrors] = useState<{ title?: string; role?: string; dates?: string }>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<OrgPublicListing | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [roles, setRoles] = useState<ItRole[]>([]);
  const [fTemplateId, setFTemplateId] = useState('');
  const toast = useToast();

  const loadListings = useCallback(async () => {
    if (!activeOrg?.id) return;
    try {
      const data = await marketplaceService.listOrgListings(activeOrg.id);
      setListings(data);
    } catch {}
  }, [activeOrg?.id]);

  useEffect(() => {
    if (!activeOrg?.id) return;
    let cancelled = false;
    const orgId = activeOrg.id;

    async function load() {
      setLoading(true);
      setError(null);

      const docPromise = orgContentService.listDocuments(orgId)
        .then(data => { if (!cancelled) setDocuments(data); })
        .catch(() => toast.error('Failed to load documents'));

      const sessionPromise = orgContentService.listSessions(orgId)
        .then(data => { if (!cancelled) setSessions(data); })
        .catch(() => toast.error('Failed to load interview sessions'));

      const listingPromise = marketplaceService.listOrgListings(orgId)
        .then(data => { if (!cancelled) setListings(data); })
        .catch(() => toast.error('Failed to load marketplace listings'));

      const templatePromise = orgContentService.listTemplates(orgId)
        .then(data => { if (!cancelled) setTemplates(data); })
        .catch(() => {});

      const rolePromise = itService.listRoles({ active_only: true })
        .then(data => { if (!cancelled) setRoles(data); })
        .catch(() => toast.error('Failed to load IT roles'));

      await Promise.allSettled([docPromise, sessionPromise, listingPromise, templatePromise, rolePromise]);
      if (!cancelled) setLoading(false);
    }

    load();
    return () => { cancelled = true; };
  }, [activeOrg?.id]);

  const resetForm = () => {
    setFTitle('');
    setFRoleId('');
    setFDescription('');
    setFMaxCandidates('');
    setFSkills('');
    setFStyle('STANDARD');
    setFTemplateId('');
    setFStartsAt('');
    setFExpiresAt('');
    setEditing(null);
    setShowForm(false);
  };

  const handleEdit = (listing: OrgPublicListing) => {
    setEditing(listing);
    setFTitle(listing.title);
    setFRoleId(listing.it_role_id);
    setFDescription(listing.description || '');
    setFMaxCandidates(listing.max_candidates?.toString() || '');
    setFSkills(listing.skills_required || '');
    setFStyle(listing.style_name || 'STANDARD');
    setFTemplateId(listing.template_id || '');
    setFStartsAt(listing.starts_at ? listing.starts_at.slice(0, 16) : '');
    setFExpiresAt(listing.expires_at ? listing.expires_at.slice(0, 16) : '');
    setShowForm(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors: { title?: string; role?: string; dates?: string } = {};
    if (!fTitle.trim()) errors.title = 'Give the listing a title.';
    if (!fRoleId) errors.role = 'Choose the IT role it is for.';
    if (fStartsAt && fExpiresAt && new Date(fStartsAt) >= new Date(fExpiresAt)) {
      errors.dates = 'The closing date has to be after the opening date.';
    }
    setFormErrors(errors);
    if (Object.keys(errors).length > 0 || !activeOrg?.id) return;
    setSaving(true);
    try {
      if (editing) {
        await marketplaceService.updateListing(editing.id, {
          title: fTitle.trim(),
          it_role_id: fRoleId,
          description: fDescription.trim() || undefined,
          interview_mode: 'typing',
          max_candidates: fMaxCandidates ? parseInt(fMaxCandidates) : undefined,
          skills_required: fSkills.trim() || undefined,
          style_name: fStyle,
          template_id: fTemplateId || undefined,
          starts_at: fStartsAt ? new Date(fStartsAt).toISOString() : undefined,
          expires_at: fExpiresAt ? new Date(fExpiresAt).toISOString() : undefined,
        });
        toast.success('Listing saved');
      } else {
        await marketplaceService.createListing({
          title: fTitle.trim(),
          it_role_id: fRoleId,
          description: fDescription.trim() || undefined,
          interview_mode: 'typing',
          max_candidates: fMaxCandidates ? parseInt(fMaxCandidates) : undefined,
          skills_required: fSkills.trim() || undefined,
          style_name: fStyle,
          template_id: fTemplateId || undefined,
          starts_at: fStartsAt ? new Date(fStartsAt).toISOString() : undefined,
          expires_at: fExpiresAt ? new Date(fExpiresAt).toISOString() : undefined,
        });
        toast.success('Listing created');
      }
      resetForm();
      await loadListings();
    } catch (err) {
      toast.error('Could not save the listing. Try again in a moment.');
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
      toast.error('Could not delete the listing.');
    }
  };

  const handleCopyLink = async (token: string) => {
    const url = `${window.location.origin}/public-interview/${token}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopiedId(token);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      toast.error('Could not copy. Your browser blocked the clipboard.');
    }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'documents', label: `Documents (${documents.length})` },
    { key: 'listings', label: `Interview listings (${listings.length})` },
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
        <button onClick={() => navigate('/org')} className="flex items-center gap-1.5 text-xs text-muted hover:text-secondary mb-4 transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to the dashboard
        </button>
        <Card>
          <div className="flex flex-col items-center py-8 text-center">
            <AlertCircle className="w-8 h-8 text-error mb-3" />
            <p className="text-sm text-primary font-medium mb-1">{error}</p>
            <button onClick={() => navigate('/org')} className="mt-3 text-sm text-action-primary hover:text-action-primary-hover transition-colors">
              Back to the dashboard
            </button>
          </div>
        </Card>
      </div>
    );
  }

  if (!activeOrg) return null;

  return (
    <div>
      {/* Who the company is: the same profile candidates see on the Opportunity Hub. */}
      <header className="mb-6">
        <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-primary">{activeOrg.name}</h1>
        <p className="mt-1 text-sm text-secondary">
          {activeOrg.website && (
            <a href={activeOrg.website} target="_blank" rel="noreferrer" className="text-action-primary hover:underline">{activeOrg.website.replace(/^https?:\/\//, '')}</a>
          )}
          {activeOrg.website && activeOrg.created_at && <span className="text-border-strong mx-2" aria-hidden>/</span>}
          {activeOrg.created_at && <span className="text-tertiary">Since {new Date(activeOrg.created_at).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</span>}
        </p>
        {activeOrg.description && <p className="text-sm text-secondary mt-2 max-w-[65ch]">{activeOrg.description}</p>}
      </header>

      <div role="tablist" aria-label="Company sections" className="flex gap-6 mb-6 border-b border-border overflow-x-auto">
        {tabs.map(t => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={`relative -mb-px pb-2.5 text-[13px] font-medium whitespace-nowrap transition-colors border-b-2 ${
              tab === t.key ? 'text-primary border-action-primary' : 'text-secondary border-transparent hover:text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-6">
          <StatStrip stats={[
            { label: 'Interviews', value: String(sessions.length) },
            { label: 'Documents', value: String(documents.length) },
            { label: 'Average score', value: avgScore !== null ? avgScore.toFixed(1) : '—', hint: avgScore !== null ? '/ 10' : undefined },
          ]} />
          {sessions.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-primary mb-3">Recent interviews</h2>
              <Card padding="none" className="overflow-hidden">
                <InterviewHistoryTable sessions={sessions.slice(0, 5)} />
              </Card>
            </section>
          )}
        </div>
      )}

      {tab === 'documents' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <DocumentUploader orgId={activeOrg.id} onUploaded={(result) => {
              const newDoc: Document = {
                id: result.doc_id,
                filename: result.filename,
                document_type: 'pdf',
                pinecone_namespace: '',
                created_at: new Date().toISOString(),
              };
              setDocuments(prev => [newDoc, ...prev]);
              orgContentService.listDocuments(activeOrg.id).then(setDocuments).catch(() => toast.error('Failed to refresh documents'));
            }} />
          </div>
          {documents.length === 0 ? (
            <Card>
              <p className="text-sm text-secondary py-8 text-center">No documents uploaded yet. Upload a PDF to add organization knowledge.</p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {documents.map(d => (
                <DocumentCard key={d.id} document={d} onDelete={async (docId) => {
                  try {
                    await orgContentService.deleteDocument(activeOrg.id, docId);
                    setDocuments(prev => prev.filter(x => x.id !== docId));
                    toast.success('Document deleted');
                  } catch {
                    toast.error('Failed to delete document');
                  }
                }} />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'listings' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[13px] text-secondary">Roles candidates can find on the Opportunity Hub and apply to.</p>
            <Button icon={<Plus />} onClick={() => { resetForm(); setFRoleId(roles[0]?.id ?? ''); setShowForm(true); }}>
              New listing
            </Button>
          </div>

          {listings.length === 0 ? (
            <div className="rounded-xl border border-border bg-section">
              <EmptyState
                icon={<ExternalLink />}
                title="No listings yet"
                description="Create one to put a role on the Opportunity Hub, where candidates can apply with their CV."
              />
            </div>
          ) : (
            <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden">
              {listings.map(listing => {
                const skills = listing.skills_required?.split(',').map(s => s.trim()).filter(Boolean) || [];
                const role = roles.find(r => r.id === listing.it_role_id);
                const expired = listing.expires_at ? new Date(listing.expires_at) < new Date() : false;
                const expiryDays = listing.expires_at ? Math.ceil((new Date(listing.expires_at).getTime() - Date.now()) / 86400000) : null;
                const status = !listing.is_open ? 'closed' : expired ? 'expired' : 'open';
                const meta = [
                  role?.name,
                  listing.style_name && listing.style_name !== 'STANDARD' ? INTERVIEW_STYLES.find(s => s.value === listing.style_name)?.label ?? listing.style_name : null,
                  listing.starts_at ? `Opens ${fmtDate(listing.starts_at)}` : null,
                  listing.expires_at ? `Closes ${fmtDate(listing.expires_at)}` : null,
                ].filter(Boolean).join(' / ');
                return (
                  <li key={listing.id} className="flex items-center gap-4 px-4 py-3 hover:bg-subtle transition-colors">
                    <button type="button" onClick={() => handleEdit(listing)} className="flex-1 min-w-0 text-left rounded">
                      <span className="flex items-center gap-2">
                        <span className="text-sm font-medium text-primary truncate">{listing.title}</span>
                        <span className={`shrink-0 inline-flex items-center gap-1.5 text-xs ${status === 'open' ? 'text-success-text' : 'text-tertiary'}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${status === 'open' ? 'bg-success' : 'bg-[var(--border-strong)]'}`} aria-hidden />
                          {status === 'open' ? 'Open' : status === 'expired' ? 'Expired' : 'Closed'}
                        </span>
                        {status === 'open' && expiryDays !== null && expiryDays > 0 && expiryDays <= 7 && (
                          <span className="shrink-0 text-xs text-warning-text">closes in {expiryDays} {expiryDays === 1 ? 'day' : 'days'}</span>
                        )}
                      </span>
                      {meta && <span className="block text-xs text-tertiary truncate mt-0.5">{meta}</span>}
                      {skills.length > 0 && <span className="block text-xs text-secondary truncate mt-0.5">{skills.join(', ')}</span>}
                    </button>
                    <span className="flex items-center gap-0.5 shrink-0">
                      <button
                        onClick={() => handleCopyLink(listing.token)}
                        className="h-8 px-2 inline-flex items-center gap-1.5 rounded-md text-xs text-secondary hover:text-primary hover:bg-hover"
                        aria-label={`Copy the link to ${listing.title}`}
                      >
                        {copiedId === listing.token ? <><Check className="w-4 h-4 text-success-text" /> Copied</> : <><Copy className="w-4 h-4" /> Link</>}
                      </button>
                      <button onClick={() => handleEdit(listing)} className="p-1.5 rounded-md text-tertiary hover:text-primary hover:bg-hover" aria-label={`Edit ${listing.title}`}>
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button onClick={() => setDeleteTarget(listing)} className="p-1.5 rounded-md text-tertiary hover:text-error-text hover:bg-hover" aria-label={`Delete ${listing.title}`}>
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      <Sheet
        open={showForm}
        onClose={resetForm}
        onSubmit={handleSave}
        width="lg"
        title={editing ? 'Edit listing' : 'New listing'}
        description={`A role ${activeOrg?.name ?? 'your organization'} shows on the Opportunity Hub. Candidates apply with their CV; you invite the ones you want to interview.`}
        footer={
          <>
            <Button type="button" variant="secondary" onClick={resetForm} disabled={saving}>Cancel</Button>
            <Button type="submit" loading={saving}>{editing ? 'Save listing' : 'Create listing'}</Button>
          </>
        }
      >
        <SheetSection title="The role">
          <Input
            label="Title"
            value={fTitle}
            onChange={e => { setFTitle(e.target.value); setFormErrors(prev => ({ ...prev, title: undefined })); }}
            placeholder="e.g. Senior backend developer"
            error={formErrors.title}
          />
          <Select
            label="IT role"
            value={fRoleId}
            onChange={v => { setFRoleId(v); setFormErrors(prev => ({ ...prev, role: undefined })); }}
            placeholder="Choose a role"
            options={roles.map(r => ({ value: r.id, label: `${r.name} (${r.family})` }))}
            error={formErrors.role}
          />
          <Textarea label="Description" value={fDescription} onChange={e => setFDescription(e.target.value)} rows={4} hint="Shown to candidates on the listing page." />
          <TagInput value={fSkills} onChange={setFSkills} label="Skills" placeholder="e.g. Python" />
        </SheetSection>

        <SheetSection title="The interview">
          <div className="space-y-1.5">
            <Select label="Interview style" value={fStyle} onChange={setFStyle} options={INTERVIEW_STYLES.map(s => ({ value: s.value, label: s.label }))} />
            <p className="text-xs text-tertiary">{INTERVIEW_STYLES.find(s => s.value === fStyle)?.desc}</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Template"
              value={fTemplateId}
              onChange={setFTemplateId}
              placeholder="No template"
              options={[{ value: '', label: 'No template' }, ...templates.map(t => ({ value: t.id, label: `${t.name} (${t.job_role})` }))]}
            />
            <Input
              label="Most candidates"
              type="number"
              min={1}
              value={fMaxCandidates}
              onChange={e => setFMaxCandidates(e.target.value)}
              placeholder="No limit"
              className="[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
            />
          </div>
        </SheetSection>

        <SheetSection title="Dates" text="Leave both empty to keep the listing open until you close it.">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <span className="block text-[13px] font-medium text-primary">Opens</span>
              <DateTimePicker value={fStartsAt} onChange={v => { setFStartsAt(v); setFormErrors(prev => ({ ...prev, dates: undefined })); }} placeholder="Right away" />
            </div>
            <div className="space-y-1.5">
              <span className="block text-[13px] font-medium text-primary">Closes</span>
              <DateTimePicker value={fExpiresAt} onChange={v => { setFExpiresAt(v); setFormErrors(prev => ({ ...prev, dates: undefined })); }} placeholder="No closing date" />
            </div>
          </div>
          {formErrors.dates && <p className="text-xs text-error">{formErrors.dates}</p>}
        </SheetSection>
      </Sheet>

      {tab === 'history' && (
        <Card>
          <InterviewHistoryTable sessions={sessions} />
        </Card>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete listing?"
        message={`"${deleteTarget?.title}" will be deleted and its link will stop working. This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => { if (deleteTarget) handleDelete(deleteTarget); setDeleteTarget(null); }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
