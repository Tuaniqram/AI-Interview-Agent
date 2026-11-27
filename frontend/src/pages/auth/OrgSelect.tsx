import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useOrg } from '../../contexts/OrgContext';
import { ChevronRight } from 'lucide-react';

export default function OrgSelect() {
  const navigate = useNavigate();
  const { memberships } = useAuth();
  const { switchOrg } = useOrg();

  const handleSelect = async (orgId: string) => {
    await switchOrg(orgId);
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-page px-4">
      <div className="w-full max-w-md space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-primary">Choose an organization</h1>
          <p className="mt-1.5 text-sm text-secondary">
            You belong to more than one. You can switch at any time from the sidebar.
          </p>
        </div>
        <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden">
          {memberships.map((m) => (
            <li key={m.org_id}>
              <button
                onClick={() => handleSelect(m.org_id)}
                className="group w-full flex items-center gap-3 px-4 py-3 hover:bg-subtle transition-colors text-left"
              >
                <span className="w-8 h-8 rounded-md bg-action-primary text-action-primary-text flex items-center justify-center text-xs font-semibold shrink-0">
                  {m.org_name?.charAt(0).toUpperCase()}
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-medium text-primary truncate">{m.org_name}</span>
                  <span className="block text-xs text-tertiary capitalize">{m.role}</span>
                </span>
                <ChevronRight className="w-4 h-4 text-tertiary group-hover:text-primary" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
