import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { Button } from '../../components/shared/Button';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { useToast } from '../../components/shared/Toast';
import { Calendar, CheckCircle, XCircle } from 'lucide-react';
import type { Application } from '../../types/marketplace';

const STATUS_LABELS: Record<string, string> = {
  applied: 'Applied',
  screening: 'In review',
  interview_offered: 'Interview offered',
  interview_accepted: 'Interview accepted',
  interview_declined: 'Declined',
  hired: 'Hired',
  rejected: 'Not selected',
};

export default function CandidateApplications() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    candidateService.getApplications()
      .then(setApplications)
      .catch(() => toast.error('Failed to load applications'))
      .finally(() => setLoading(false));
  }, []);

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

      {applications.length === 0 ? (
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
                      {application.fit_score != null && (
                        <span>Fit {application.fit_score.toFixed(1)}/10</span>
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
