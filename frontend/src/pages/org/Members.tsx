import { useCallback, useEffect, useMemo, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { useAuth } from '../../contexts/AuthContext';
import { MemberList } from '../../components/org/MemberList';
import { PageHeader } from '../../components/shared/PageHeader';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import type { OrgMember, OrgRole } from '../../types/org';
import { orgService } from '../../services/orgService';
import { useToast } from '../../components/shared/Toast';

export default function Members() {
  const { activeOrg } = useOrg();
  const { user, memberships } = useAuth();
  const toast = useToast();
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [loading, setLoading] = useState(true);

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
      <PageHeader
        title="Team Members"
        description="Manage your organization's members and their roles"
      />
      <MemberList
        members={members}
        activeRole={activeRole}
        currentUserId={user?.id}
        onRoleChange={handleRoleChange}
        onRemove={handleRemove}
      />
    </div>
  );
}
