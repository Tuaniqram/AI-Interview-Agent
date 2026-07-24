import { useState, useEffect, useCallback } from 'react';
import { PageHeader } from '../../components/shared/PageHeader';
import { Button } from '../../components/shared/Button';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { marketplaceService } from '../../services/marketplaceService';
import { departmentService, type Department } from '../../services/departmentService';
import { useOrg } from '../../contexts/OrgContext';
import { useAuth } from '../../contexts/AuthContext';
import { Copy, Plus, Pencil, Trash2, ExternalLink, Clock } from 'lucide-react';
import type { OrgPublicListing } from '../../types/marketplace';

export default function PublicListings() {
  const { activeOrg, members } = useOrg();
  const { user } = useAuth();
  const [listings, setListings] = useState<OrgPublicListing[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<OrgPublicListing | null>(null);
  const [title, setTitle] = useState('');
  const [departmentId, setDepartmentId] = useState<number>(0);
  const [description, setDescription] = useState('');
  const [interviewMode, setInterviewMode] = useState('typing');
  const [maxCandidates, setMaxCandidates] = useState('');
  const [skillsRequired, setSkillsRequired] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [saving, setSaving] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const orgId = activeOrg?.id;

  const loadListings = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    try {
      const [listingData, deptData] = await Promise.all([
        marketplaceService.listOrgListings(orgId),
        departmentService.listDepartments(),
      ]);
      setListings(listingData);
      setDepartments(deptData);
    } catch (err) {
      console.error('Failed to load listings:', err);
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    loadListings();
  }, [loadListings]);

  const resetForm = () => {
    setTitle('');
    setDepartmentId(0);
    setDescription('');
    setInterviewMode('typing');
    setMaxCandidates('');
    setSkillsRequired('');
    setStartsAt('');
    setExpiresAt('');
    setEditing(null);
    setShowForm(false);
  };

  const handleEdit = (listing: OrgPublicListing) => {
    setEditing(listing);
    setTitle(listing.title);
    setDepartmentId(listing.department_id || 0);
    setDescription(listing.description || '');
    setInterviewMode(listing.interview_mode);
    setMaxCandidates(listing.max_candidates?.toString() || '');
    setSkillsRequired(listing.skills_required || '');
    setStartsAt(listing.starts_at ? listing.starts_at.slice(0, 16) : '');
    setExpiresAt(listing.expires_at ? listing.expires_at.slice(0, 16) : '');
    setShowForm(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !departmentId) return;
    setSaving(true);
    try {
      if (editing) {
        await marketplaceService.updateListing(editing.id, {
          title: title.trim(),
          department_id: departmentId,
          description: description.trim() || undefined,
          interview_mode: interviewMode,
          max_candidates: maxCandidates ? parseInt(maxCandidates) : undefined,
          skills_required: skillsRequired.trim() || undefined,
          starts_at: startsAt ? new Date(startsAt).toISOString() : undefined,
          expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
        });
      } else {
        await marketplaceService.createListing({
          title: title.trim(),
          department_id: departmentId,
          description: description.trim() || undefined,
          interview_mode: interviewMode,
          max_candidates: maxCandidates ? parseInt(maxCandidates) : undefined,
          skills_required: skillsRequired.trim() || undefined,
          starts_at: startsAt ? new Date(startsAt).toISOString() : undefined,
          expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
        });
      }
      resetForm();
      await loadListings();
    } catch (err) {
      console.error('Failed to save listing:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to close this listing?')) return;
    try {
      await marketplaceService.deleteListing(id);
      await loadListings();
    } catch (err) {
      console.error('Failed to delete listing:', err);
    }
  };

  const handleCopyLink = (token: string) => {
    const url = `${window.location.origin}/public-interview/${token}`;
    navigator.clipboard.writeText(url);
    setCopiedId(token);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const isOwner = user?.id ? members.some(m => m.user_id === user.id && m.role === 'owner') : false;

  const formatDate = (d: string | null) => d ? new Date(d).toLocaleDateString() : null;
  const isExpired = (d: string | null) => d ? new Date(d) < new Date() : false;
  const daysUntil = (d: string | null) => {
    if (!d) return null;
    const diff = Math.ceil((new Date(d).getTime() - Date.now()) / 86400000);
    return diff;
  };

  if (loading) return <LoadingSpinner message="Loading listings..." />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Public Interview Links"
        description="Create and manage public interview links for the marketplace"
        actions={isOwner ? (
          <Button onClick={() => { resetForm(); setShowForm(true); }}>
            <Plus className="w-4 h-4 mr-1.5" /> Create Link
          </Button>
        ) : undefined}
      />

      {showForm && (
        <form onSubmit={handleSave} className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-4">
          <h3 className="font-semibold text-[var(--text-primary)]">{editing ? 'Edit Listing' : 'New Listing'}</h3>

          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Title *</label>
            <input type="text" value={title} onChange={e => setTitle(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" required />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Department *</label>
            <select value={departmentId} onChange={e => setDepartmentId(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" required>
              <option value={0}>-- Select department --</option>
              {departments.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Interview Mode</label>
              <select value={interviewMode} onChange={e => setInterviewMode(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]">
                <option value="typing">Typing</option>
                <option value="voice">Voice</option>
                <option value="avatar">Avatar</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Max Candidates</label>
              <input type="number" value={maxCandidates} onChange={e => setMaxCandidates(e.target.value)} min={1}
                placeholder="Unlimited"
                className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Skills Required</label>
            <input type="text" value={skillsRequired} onChange={e => setSkillsRequired(e.target.value)}
              placeholder="e.g. Python, React, AWS"
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Starts At</label>
              <input type="datetime-local" value={startsAt} onChange={e => setStartsAt(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Expires At</label>
              <input type="datetime-local" value={expiresAt} onChange={e => setExpiresAt(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" />
            </div>
          </div>

          <div className="flex gap-3">
            <Button type="submit" loading={saving}>{editing ? 'Save Changes' : 'Create'}</Button>
            <Button type="button" variant="ghost" onClick={resetForm}>Cancel</Button>
          </div>
        </form>
      )}

      {listings.length === 0 ? (
        <div className="bg-[var(--bg-section)] rounded-xl p-12 text-center border border-[var(--border-color)]">
          <ExternalLink className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-3" />
          <h3 className="font-semibold text-[var(--text-primary)] mb-1">No public links yet</h3>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            Create a public interview link to share with candidates via the marketplace
          </p>
          {isOwner && (
            <Button onClick={() => { resetForm(); setShowForm(true); }}>
              <Plus className="w-4 h-4 mr-1.5" /> Create Your First Link
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {listings.map(listing => {
            const expiryDays = daysUntil(listing.expires_at);
            const expired = isExpired(listing.expires_at);
            const skills = listing.skills_required?.split(',').map(s => s.trim()).filter(Boolean) || [];
            return (
              <div key={listing.id} className="bg-[var(--bg-section)] rounded-xl p-5 border border-[var(--border-color)] flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="font-semibold text-[var(--text-primary)] truncate">{listing.title}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium uppercase ${listing.is_open ? 'bg-green-500/15 text-green-500' : 'bg-red-500/15 text-red-500'}`}>
                      {listing.is_open ? 'Open' : 'Closed'}
                    </span>
                    {expired && listing.is_open && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-500/15 text-red-500">Expired</span>
                    )}
                    {expiryDays !== null && expiryDays > 0 && expiryDays <= 7 && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-yellow-500/15 text-yellow-500">
                        Expires in {expiryDays}d
                      </span>
                    )}
                  </div>
                  {listing.department_name && (
                    <p className="text-xs text-[var(--text-muted)] mb-1">{listing.department_name}</p>
                  )}
                  {listing.description && (
                    <p className="text-sm text-[var(--text-secondary)] line-clamp-2 mb-2">{listing.description}</p>
                  )}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs px-2 py-0.5 rounded bg-[var(--action-primary)]/10 text-[var(--action-primary)]">
                      {listing.interview_mode}
                    </span>
                    {skills.map(skill => (
                      <span key={skill} className="text-xs px-2 py-0.5 rounded bg-[var(--bg-page)] text-[var(--text-muted)] border border-[var(--border-color)]">
                        {skill}
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-[var(--text-muted)] mt-2">
                    {listing.starts_at && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Starts {formatDate(listing.starts_at)}</span>}
                    {listing.expires_at && <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Expires {formatDate(listing.expires_at)}</span>}
                    {listing.max_candidates && <span>Max: {listing.max_candidates}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button variant="ghost" size="sm" onClick={() => handleCopyLink(listing.token)} title="Copy link">
                    {copiedId === listing.token ? <span className="text-green-500">Copied!</span> : <Copy className="w-4 h-4" />}
                  </Button>
                  {isOwner && (
                    <>
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(listing)} title="Edit">
                        <Pencil className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(listing.id)} title="Close listing">
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
