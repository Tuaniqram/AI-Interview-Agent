import { useState } from 'react';
import { UserMinus } from 'lucide-react';
import type { OrgMember, OrgRole } from '../../types/org';
import { ConfirmDialog } from '../shared/ConfirmDialog';

interface MemberListProps {
  members: OrgMember[];
  activeRole?: OrgRole;
  currentUserId?: string;
  onRoleChange?: (memberId: string, newRole: string) => void;
  onRemove?: (memberId: string, memberName: string) => void;
}

const roleColors: Record<string, string> = {
  owner: 'bg-purple-500/15 text-purple-500',
  member: 'bg-blue-500/15 text-blue-500',
  viewer: 'bg-green-500/15 text-green-500',
};

function Avatar({ name, email }: { name: string; email: string }) {
  const initial = (name || email || '?').charAt(0).toUpperCase();
  return (
    <div className="w-8 h-8 rounded-full bg-action-primary/20 flex items-center justify-center text-sm font-semibold text-action-primary shrink-0">
      {initial}
    </div>
  );
}

export function MemberList({ members, activeRole, currentUserId, onRoleChange, onRemove }: MemberListProps) {
  const [removeTarget, setRemoveTarget] = useState<OrgMember | null>(null);

  if (members.length === 0) {
    return (
      <div className="bg-elevated rounded-xl p-8 text-center border border-[var(--border-color)]">
        <p className="text-sm text-secondary">No members yet.</p>
      </div>
    );
  }

  return (
    <>
      <div className="bg-elevated rounded-xl border border-[var(--border-color)] divide-y divide-[var(--border-color)] overflow-hidden">
        {members.map((member) => {
          const isOwner = activeRole === 'owner';
          const isSelf = currentUserId === member.user_id;
          const canManage = isOwner && !isSelf && member.role !== 'owner';

          return (
            <div key={member.id} className="flex items-center gap-3 px-4 py-3 hover:bg-section/50 transition-colors">
              <Avatar name={member.name} email={member.email} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-primary truncate">
                  {member.name}
                  {isSelf && <span className="text-xs text-muted ml-1.5 font-normal">(you)</span>}
                </p>
                <p className="text-xs text-muted truncate">{member.email}</p>
              </div>
              <div className="flex items-center gap-2">
                {onRoleChange && canManage ? (
                  <select
                    value={member.role}
                    onChange={(e) => onRoleChange(member.user_id, e.target.value)}
                    className="text-xs rounded-lg border border-[var(--border-color)] bg-page px-2 py-1 text-primary focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
                    aria-label={`Role for ${member.name}`}
                  >
                    <option value="member">Member</option>
                    <option value="viewer">Viewer</option>
                  </select>
                ) : (
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${roleColors[member.role] || ''}`}>
                    {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                  </span>
                )}
                {onRemove && canManage && (
                  <button
                    onClick={() => setRemoveTarget(member)}
                    className="p-1.5 rounded-lg text-muted hover:text-error hover:bg-error-bg transition-colors"
                    title={`Remove ${member.name}`}
                    aria-label={`Remove ${member.name}`}
                  >
                    <UserMinus className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              <div className="text-xs text-muted w-20 text-right shrink-0">
                {member.joined_at ? new Date(member.joined_at).toLocaleDateString() : '-'}
              </div>
            </div>
          );
        })}
      </div>

      <ConfirmDialog
        open={!!removeTarget}
        title="Remove Member"
        message={`Are you sure you want to remove ${removeTarget?.name} from the organization?`}
        confirmLabel="Remove"
        variant="danger"
        onConfirm={() => {
          if (removeTarget) onRemove?.(removeTarget.user_id, removeTarget.name);
          setRemoveTarget(null);
        }}
        onCancel={() => setRemoveTarget(null)}
      />
    </>
  );
}