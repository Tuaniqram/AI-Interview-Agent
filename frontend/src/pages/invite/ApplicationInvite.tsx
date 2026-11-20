import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { CheckCircle, Clock, Crosshair, Frown, XCircle } from 'lucide-react';
import { marketplaceService } from '../../services/marketplaceService';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { Button } from '../../components/shared/Button';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { setInterviewAccess } from '../../utils/interviewAccess';
import type { ApplicationInvitation } from '../../types/marketplace';

/** Public page behind the emailed link. No login needed: the token is the credential. */
export default function ApplicationInvite() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { candidate, logout } = useCandidateAuth();
  const [invite, setInvite] = useState<ApplicationInvitation | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [acting, setActing] = useState<'accepted' | 'declined' | null>(null);

  useEffect(() => {
    if (!token) return;
    marketplaceService.getApplicationInvitation(token)
      .then(setInvite)
      .catch((err: any) =>
        setLoadError(err?.response?.status === 404
          ? 'This invitation link is not valid. Check that you copied the whole link from your email.'
          : 'We could not load this invitation. Please try again.'))
      .finally(() => setLoading(false));
  }, [token]);

  const respond = async (response: 'accepted' | 'declined') => {
    if (!token) return;
    setActionError('');
    setActing(response);
    try {
      const updated = await marketplaceService.respondToApplicationInvitation(token, response);
      setInvite(updated);
      if (response === 'accepted' && updated.session_id) {
        setInterviewAccess(updated.session_id, updated.access_token);
        navigate(`/interview/${updated.session_id}`);
      }
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setActing(null);
    }
  };

  const shell = (children: React.ReactNode) => (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4 py-10">
      <div className="w-full max-w-md space-y-6">{children}</div>
    </div>
  );

  if (loading) return shell(<ContentSkeleton />);

  if (loadError || !invite) {
    return shell(
      <div className="text-center" role="alert">
        <Frown size={48} className="mx-auto mb-4 text-muted" />
        <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Invitation not found</h1>
        <p className="text-[var(--text-secondary)]">{loadError}</p>
        <Link to="/opportunity-hub" className="inline-block mt-4 text-sm text-[var(--action-primary)] hover:underline">
          Browse open interviews
        </Link>
      </div>
    );
  }

  // A different candidate account is signed in: the interview socket would refuse the session.
  const wrongAccount = !!candidate && candidate.email.toLowerCase() !== invite.candidate_email.toLowerCase();
  const expires = invite.expires_at ? new Date(invite.expires_at).toLocaleDateString(undefined, { dateStyle: 'medium' }) : null;
  const accepted = invite.candidate_response === 'accepted';
  const declined = invite.candidate_response === 'declined';

  return shell(
    <>
      <div className="text-center">
        <Crosshair size={48} className="mx-auto mb-3 text-action-primary" />
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">
          {declined ? 'Invitation declined' : "You're invited to interview"}
        </h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          {invite.org_name ? <><strong>{invite.org_name}</strong> would like to interview you.</> : 'You have been invited to interview.'}
        </p>
      </div>

      <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-3 text-left">
        <div>
          <span className="text-sm text-[var(--text-secondary)]">Position</span>
          <p className="font-semibold text-[var(--text-primary)]">{invite.job_title}</p>
        </div>
        {invite.org_name && (
          <div>
            <span className="text-sm text-[var(--text-secondary)]">Organization</span>
            <p className="font-semibold text-[var(--text-primary)]">{invite.org_name}</p>
          </div>
        )}
        <div>
          <span className="text-sm text-[var(--text-secondary)]">Candidate</span>
          <p className="font-semibold text-[var(--text-primary)]">{invite.candidate_name}</p>
          <p className="text-sm text-[var(--text-secondary)] break-all">{invite.candidate_email}</p>
        </div>
        {expires && invite.can_respond && (
          <p className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
            <Clock className="w-3.5 h-3.5" /> Respond by {expires}
          </p>
        )}
      </div>

      {wrongAccount && (
        <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3 text-sm text-[var(--text-primary)]" role="alert">
          This invitation is for {invite.candidate_email}, but you are signed in as {candidate?.email}. Sign out to
          take this interview, or sign in with the invited email.
          <div className="mt-2">
            <Button size="sm" variant="outline" onClick={logout}>Sign out</Button>
          </div>
        </div>
      )}

      {actionError && (
        <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 border border-red-500/20" role="alert">{actionError}</div>
      )}

      {invite.can_respond && (
        <div className="flex flex-col sm:flex-row gap-3">
          <Button className="flex-1" loading={acting === 'accepted'} disabled={acting !== null || wrongAccount}
            onClick={() => respond('accepted')}>
            <CheckCircle className="w-4 h-4 mr-1" /> Accept &amp; start interview
          </Button>
          <Button className="flex-1" variant="outline" loading={acting === 'declined'} disabled={acting !== null}
            onClick={() => respond('declined')}>
            <XCircle className="w-4 h-4 mr-1" /> Decline
          </Button>
        </div>
      )}

      {accepted && invite.session_id && (
        <Button className="w-full" disabled={wrongAccount} onClick={() => {
          setInterviewAccess(invite.session_id!, invite.access_token);
          navigate(`/interview/${invite.session_id}`);
        }}>
          Continue to your interview
        </Button>
      )}
      {accepted && !invite.session_id && (
        <p className="text-center text-sm text-[var(--text-secondary)]">
          You accepted this invitation, but the interview is no longer available. Please contact {invite.org_name || 'the organization'}.
        </p>
      )}
      {declined && (
        <p className="text-center text-sm text-[var(--text-secondary)]">You declined this invitation. Thank you for letting them know.</p>
      )}
      {!invite.can_respond && !accepted && !declined && (
        <p className="text-center text-sm text-[var(--text-secondary)]" role="status">
          {invite.expired
            ? 'This invitation has expired. Please contact the organization if you are still interested.'
            : 'This invitation is no longer active.'}
        </p>
      )}

      <p className="text-center text-xs text-[var(--text-secondary)]">
        No account needed. Want to keep your applications and results?{' '}
        <Link to="/candidate/register" className="text-[var(--action-primary)] hover:underline">Create an account</Link>{' '}
        with {invite.candidate_email}.
      </p>
    </>
  );
}
