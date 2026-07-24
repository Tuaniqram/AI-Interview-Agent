import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Frown, Crosshair } from 'lucide-react';
import { invitationService } from '../../services/invitationService';
import { Button } from '../../components/shared/Button';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';

export default function AcceptInvitation() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [invite, setInvite] = useState<{
    candidate_name: string;
    candidate_email: string;
    job_role: string;
    department_name: string | null;
  } | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    if (!token) return;
    invitationService.verify(token)
      .then((data) => {
        if (data.valid) {
          setInvite(data);
        } else {
          setError('Invalid invitation');
        }
      })
      .catch((err) => setError(err?.response?.data?.detail || 'Invalid or expired invitation'))
      .finally(() => setLoading(false));
  }, [token]);

  const handleAccept = async () => {
    if (!token) return;
    setAccepting(true);
    try {
      const res = await invitationService.accept(token);
      navigate(`/interview/${res.session_id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to accept invitation');
    } finally {
      setAccepting(false);
    }
  };

  if (loading) return <LoadingSpinner message="Verifying invitation..." />;

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
        <div className="text-center max-w-md">
          <Frown size={48} className="mx-auto mb-4 text-muted" />
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Invitation Not Found</h1>
          <p className="text-[var(--text-secondary)]">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
      <div className="w-full max-w-md text-center space-y-6">
        <Crosshair size={48} className="mx-auto text-action-primary" />
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">You're Invited!</h1>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-3 text-left">
          <div>
            <span className="text-sm text-[var(--text-secondary)]">Position</span>
            <p className="font-semibold text-[var(--text-primary)]">{invite?.job_role}</p>
          </div>
          {invite?.department_name && (
            <div>
              <span className="text-sm text-[var(--text-secondary)]">Department</span>
              <p className="font-semibold text-[var(--text-primary)]">{invite.department_name}</p>
            </div>
          )}
          <div>
            <span className="text-sm text-[var(--text-secondary)]">Candidate</span>
            <p className="font-semibold text-[var(--text-primary)]">{invite?.candidate_name}</p>
          </div>
        </div>
        <Button onClick={handleAccept} loading={accepting} className="w-full">
          Accept & Start Interview
        </Button>
      </div>
    </div>
  );
}
