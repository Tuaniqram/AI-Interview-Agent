import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useOrg } from '../../contexts/OrgContext';

export default function OrgSelect() {
  const navigate = useNavigate();
  const { memberships } = useAuth();
  const { switchOrg } = useOrg();

  const handleSelect = async (orgId: string) => {
    await switchOrg(orgId);
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Select Organization</h1>
          <p className="mt-2 text-[var(--text-secondary)]">
            Choose which organization to work with
          </p>
        </div>
        <div className="space-y-3">
          {memberships.map((m) => (
            <button
              key={m.org_id}
              onClick={() => handleSelect(m.org_id)}
              className="w-full p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors text-left"
            >
              <div className="font-medium text-[var(--text-primary)]">{m.org_name}</div>
              <div className="text-sm text-[var(--text-secondary)]">Role: {m.role}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
