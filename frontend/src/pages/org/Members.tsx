import { useCallback, useEffect, useMemo, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { useAuth } from '../../contexts/AuthContext';
import { MemberList } from '../../components/org/MemberList';
import { PageHeader } from '../../components/shared/PageHeader';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { UserPlus, X, Loader2 } from 'lucide-react';
import type { OrgMember, OrgRole } from '../../types/org';
import { orgService } from '../../services/orgService';
import { useToast } from '../../components/shared/Toast';

function AddMemberModal({ open, onClose, onAdd }: {
  open: boolean;
  onClose: () => void;
  onAdd: (email: string, role: string) => Promise<void>;
}) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('member');
  const [adding, setAdding] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdding(true);
    try {
      await onAdd(email, role);
      setEmail('');
      onClose();
    } catch {
    } finally {
      setAdding(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-overlay/50">
      <div className="bg-elevated rounded-xl shadow-lg max-w-md w-full mx-4 p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-semibold text-primary">Invite Member</h3>
          <button onClick={onClose} className="text-muted hover:text-secondary p-1"><X className="w-4 h-4" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              placeholder="colleague@company.com"
              className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] border border-[var(--border-color)]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-secondary mb-1.5">Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-input text-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] border border-[var(--border-color)]"
            >
              <option value="member">Member</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-action-ghost-text bg-action-ghost-hover rounded-lg hover:bg-action-secondary-hover transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={adding}
              className="px-4 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors inline-flex items-center gap-2">
              {adding && <Loader2 className="w-4 h-4 animate-spin" />}
              Send Invitation
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Members() {
  const { activeOrg } = useOrg();
  const { user, memberships } = useAuth();
  const toast = useToast();
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  const activeRole = useMemo<OrgRole | undefined>(() => {
    if (!activeOrg) return undefined;
    const m = memberships.find(m => m.org_id === activeOrg.id);
    return m?.role as OrgRole | undefined;
  }, [activeOrg, memberships]);

  const loadMembers = useCallback(() => {
    if (!activeOrg) return;
    setLoading(true);
    orgService.listMembers(activeOrg.id)
      .then(setMembers)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [activeOrg]);

  useEffect(() => { loadMembers(); }, [loadMembers]);

  const handleAddMember = useCallback(async (email: string, role: string) => {
    if (!activeOrg) return;
    try {
      await orgService.inviteMember(activeOrg.id, email, role);
      toast.success(`Invitation sent to ${email}`);
      loadMembers();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Failed to invite member';
      toast.error(msg);
      throw err;
    }
  }, [activeOrg, loadMembers, toast]);

  const handleRoleChange = useCallback(async (memberUserId: string, newRole: string) => {
    if (!activeOrg) return;
    try {
      await orgService.updateMemberRole(activeOrg.id, memberUserId, newRole);
      toast.success('Member role updated');
      loadMembers();
    } catch (err) {
      toast.error('Failed to update role');
    }
  }, [activeOrg, loadMembers, toast]);

  const handleRemove = useCallback(async (memberUserId: string, memberName: string) => {
    if (!activeOrg) return;
    try {
      await orgService.removeMember(activeOrg.id, memberUserId);
      toast.success(`${memberName} removed from organization`);
      loadMembers();
    } catch (err) {
      toast.error('Failed to remove member');
    }
  }, [activeOrg, loadMembers, toast]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader
          title="Team Members"
          description="Manage your organization's members and their roles"
        />
        {activeRole === 'owner' && (
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            Invite Member
          </button>
        )}
      </div>
      <MemberList
        members={members}
        activeRole={activeRole}
        currentUserId={user?.id}
        onRoleChange={handleRoleChange}
        onRemove={handleRemove}
      />
      <AddMemberModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddMember}
      />
    </div>
  );
}
