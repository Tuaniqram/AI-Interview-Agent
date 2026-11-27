import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { Button } from '../../components/shared/Button';
import { Card } from '../../components/shared/Card';
import { PageHeader } from '../../components/shared/PageHeader';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { useToast } from '../../components/shared/Toast';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { Briefcase, Calendar, Check, FileText, Mail, X } from 'lucide-react';
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
    <div>
      <PageHeader
        title="Applications"
        description="Roles you applied for, and interview invitations waiting for your answer."
      />

      {needsVerification ? (
        <div className="p-5 rounded-xl bg-warning-bg space-y-3" role="alert">
          <p className="text-sm font-semibold text-warning-text">Verify your email to see your applications</p>
          <p className="text-[13px] text-secondary max-w-[65ch]">
            Applications you made as a guest with this email will appear here, with your CV and interview history,
            once your email is verified.
          </p>
          <Button size="sm" variant="secondary" icon={<Mail />} loading={sendingVerification} onClick={handleResendVerification}>
            Resend verification email
          </Button>
        </div>
      ) : applications.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Briefcase />}
            title="No applications yet"
            description="Browse the Opportunity Hub and apply to an open interview. It shows up here with its status."
            action={<Link to="/opportunity-hub"><Button variant="secondary">Browse open interviews</Button></Link>}
          />
        </Card>
      ) : (
        <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)]">
          {applications.map((application) => {
            const canRespond = application.org_decision === 'invited' && application.candidate_response === 'pending';
            const canStart = application.candidate_response === 'accepted' && application.session_id;
            const status = STATUS_LABELS[application.status] || application.status;

            return (
              <li key={application.id} className="px-4 py-4 sm:px-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-primary truncate">
                      {application.public_title || 'IT Interview'}
                    </h3>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-tertiary">
                      <span className={`h-5 px-1.5 rounded-md flex items-center font-medium ${canRespond ? 'bg-action-primary-soft text-action-primary' : 'bg-hover text-secondary'}`}>
                        {status}
                      </span>
                      {application.fit_score != null ? (
                        <span className="tabular">Fit {application.fit_score.toFixed(1)} / 10</span>
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
                      <p className="text-[13px] text-secondary mt-2 line-clamp-2 max-w-[70ch]">{application.fit_summary}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {canRespond && (
                      <>
                        <Button size="sm" variant="secondary" icon={<X />} disabled={acting === application.id}
                          onClick={() => handleRespond(application, 'declined')}>
                          Decline
                        </Button>
                        <Button size="sm" icon={<Check />} loading={acting === application.id}
                          onClick={() => handleRespond(application, 'accepted')}>
                          Accept interview
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
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
