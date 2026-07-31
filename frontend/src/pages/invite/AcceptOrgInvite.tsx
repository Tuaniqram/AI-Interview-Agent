import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Building2, UserCheck } from 'lucide-react';
import { orgService } from '../../services/orgService';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../../components/shared/Button';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import type { OrgInvitationVerifyResponse } from '../../types/org';

export default function AcceptOrgInvite() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [invite, setInvite] = useState<OrgInvitationVerifyResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    if (!token) return;
    orgService.verifyOrgInvitation(token)
      .then((data) => {
        if (data.valid) setInvite(data);
        else setError('Invalid invitation');
      })
      .catch((err) => setError(err?.response?.data?.detail || 'Invalid or expired invitation'))
      .finally(() => setLoading(false));
  }, [token]);

  const handleAccept = async () => {
    if (!token) return;
    if (!isAuthenticated) {
      navigate(`/login?redirect=/accept-org-invite/${token}`);
      return;
    }
    setAccepting(true);
    try {
      await orgService.acceptOrgInvitation(token);
      setAccepted(true);
      setTimeout(() => navigate('/org'), 2000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to accept invitation');
    } finally {
      setAccepting(false);
    }
  };

  if (loading) return <ContentSkeleton />;

  if (error && !invite) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
        <div className="text-center max-w-md">
          <Building2 size={48} className="mx-auto mb-4 text-muted" />
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Invitation Not Found</h1>
          <p className="text-[var(--text-secondary)]">{error}</p>
        </div>
      </div>
    );
  }

  if (accepted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
        <div className="text-center max-w-md">
          <UserCheck size={48} className="mx-auto mb-4 text-green-500" />
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Welcome to the team!</h1>
          <p className="text-[var(--text-secondary)]">You've joined {invite?.org_name}. Redirecting...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
      <div className="w-full max-w-md text-center space-y-6">
        <Building2 size={48} className="mx-auto text-action-primary" />
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Join {invite?.org_name}</h1>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-3 text-left">
          <div>
            <span className="text-sm text-[var(--text-secondary)]">Invited by</span>
            <p className="font-semibold text-[var(--text-primary)]">{invite?.inviter_name}</p>
          </div>
          <div>
            <span className="text-sm text-[var(--text-secondary)]">Organization</span>
            <p className="font-semibold text-[var(--text-primary)]">{invite?.org_name}</p>
          </div>
          <div>
            <span className="text-sm text-[var(--text-secondary)]">Role</span>
            <p className="font-semibold text-[var(--text-primary)] capitalize">{invite?.role}</p>
          </div>
        </div>
        {error && (
          <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600 dark:text-red-400">{error}</div>
        )}
        {!isAuthenticated ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--text-secondary)]">Sign in or create an account to accept this invitation.</p>
            <Button onClick={handleAccept} className="w-full">Sign in to accept</Button>
            <Link to={`/register?redirect=/accept-org-invite/${token}`} className="block text-sm text-[var(--action-primary)] hover:underline">
              Don't have an account? Create one
            </Link>
          </div>
        ) : (
          <Button onClick={handleAccept} loading={accepting} className="w-full">
            {accepting ? 'Accepting...' : 'Accept & Join'}
          </Button>
        )}
      </div>
    </div>
  );
}
