import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { Button } from '../../components/shared/Button';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { useToast } from '../../components/shared/Toast';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { Calendar, CheckCircle, FileText, Mail, XCircle } from 'lucide-react';
import type { Application, FitStatus } from '../../types/marketplace';

const STATUS_LABELS: Record<string, string> = {
  applied: 'Applied',
  screening: 'In review',
  evaluated: 'In review',
  interview_offered: 'Interview offered',
  interview_accepted: 'Interview accepted',
  interview_declined: 'Declined',
  hired: 'Hired',
  rejected: 'Not selected',
};

const FIT_STATUS_LABELS: Record<FitStatus, string> = {
  pending: 'Evaluation queued',
  running: 'Evaluating…',
  completed: 'Evaluated',
  failed: 'Evaluation unavailable',
};

export default function CandidateApplications() {
  const { sendVerification } = useCandidateAuth();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [acting, setActing] = useState<string | null>(null);
  const [sendingVerification, setSendingVerification] = useState(false);
  const toast = useToast();

  useEffect(() => {
    candidateService.getApplications()
      .then(setApplications)
      .catch((err: any) => {
        // History stays hidden until the email is verified (also protects claimed guest profiles).
        if (err?.response?.status === 403) setNeedsVerification(true);
        else toast.error('Failed to load applications');
      })
      .finally(() => setLoading(false));
  }, []);

  const handleResendVerification = async () => {
    setSendingVerification(true);
    try {
      await sendVerification();
      toast.success('Verification email sent');
    } catch {
      toast.error('Could not send verification email');
    } finally {
      setSendingVerification(false);
    }
  };

  const handleRespond = async (application: Application, response: 'accepted' | 'declined') => {
    setActing(application.id);
    try {
      const updated = await candidateService.respondToApplication(application.id, response);
      setApplications(prev => prev.map(a => a.id === updated.id ? updated : a));
      toast.success(response === 'accepted' ? 'Interview accepted' : 'Invitation declined');
    } catch {
      toast.error('Failed to update application');
    } finally {
      setActing(null);
    }
  };

  if (loading) return <ContentSkeleton />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">My Applications</h1>
        <p className="text-[var(--text-secondary)] mt-1">Track applications and interview invitations</p>
      </div>

      {needsVerification ? (
        <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-3" role="alert">
          <p className="font-semibold text-[var(--text-primary)]">Verify your email to see your applications</p>
          <p className="text-sm text-[var(--text-secondary)]">
            Applications you made as a guest with this email will appear here, with your CV and interview history,
            once your email is verified.
          </p>
          <Button size="sm" loading={sendingVerification} onClick={handleResendVerification}>
            <Mail className="w-4 h-4 mr-1" /> Resend verification email
          </Button>
        </div>
      ) : applications.length === 0 ? (
        <EmptyState
          title="No applications yet"
          description="Browse the Opportunity Hub and apply to open IT interviews."
        />
      ) : (
        <div className="space-y-3">
          {applications.map((application) => {
            const canRespond = application.org_decision === 'invited' && application.candidate_response === 'pending';
            const canStart = application.candidate_response === 'accepted' && application.session_id;
            const status = STATUS_LABELS[application.status] || application.status;

            return (
              <div key={application.id} className="p-5 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)]">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="font-semibold text-[var(--text-primary)] truncate">
                      {application.public_title || 'IT Interview'}
                    </h3>
                    <div className="flex items-center gap-2 mt-1 text-xs text-[var(--text-secondary)]">
                      <span className="px-2 py-0.5 rounded-full bg-[var(--action-primary)]/10 text-[var(--action-primary)]">
                        {status}
                      </span>
                      {application.fit_score != null ? (
                        <span>Fit {application.fit_score.toFixed(1)}/10</span>
                      ) : (
                        <span>{FIT_STATUS_LABELS[application.fit_status] ?? application.fit_status}</span>
                      )}
                      {application.resume_filename && (
                        <span className="flex items-center gap-1 truncate max-w-[14rem]" title={application.resume_filename}>
                          <FileText className="w-3 h-3 shrink-0" />
                          <span className="truncate">{application.resume_filename}</span>
                        </span>
                      )}
                      {application.created_at && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(application.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    {application.fit_summary && (
                      <p className="text-sm text-[var(--text-secondary)] mt-2 line-clamp-2">{application.fit_summary}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {canRespond && (
                      <>
                        <Button size="sm" loading={acting === application.id}
                          onClick={() => handleRespond(application, 'accepted')}>
                          <CheckCircle className="w-4 h-4 mr-1" /> Accept
                        </Button>
                        <Button size="sm" variant="ghost" disabled={acting === application.id}
                          onClick={() => handleRespond(application, 'declined')}>
                          <XCircle className="w-4 h-4 mr-1" /> Decline
                        </Button>
                      </>
                    )}
                    {canStart && (
                      <Link to={`/interview/${application.session_id}`}>
                        <Button size="sm">Start interview</Button>
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
