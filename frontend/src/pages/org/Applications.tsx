import { useEffect, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { marketplaceService } from '../../services/marketplaceService';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { CardSkeleton } from '../../components/shared/Skeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Button } from '../../components/shared/Button';
import { useToast } from '../../components/shared/Toast';
import { Briefcase, CheckCircle, Mail, XCircle } from 'lucide-react';
import type { Application } from '../../types/marketplace';

const STATUS_LABELS: Record<string, string> = {
  applied: 'Applied',
  screening: 'In review',
  interview_offered: 'Invited',
  interview_accepted: 'Accepted',
  interview_declined: 'Declined',
  hired: 'Hired',
  rejected: 'Rejected',
};

export default function OrgApplications() {
  const { activeOrg } = useOrg();
  const [applications, setApplications] = useState<Application[]>([]);
  const [fitDrafts, setFitDrafts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const toast = useToast();

  const load = async () => {
    if (!activeOrg?.id) return;
    setLoading(true);
    try {
      const data = await marketplaceService.listOrgApplications(activeOrg.id);
      setApplications(data);
    } catch {
      toast.error('Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [activeOrg?.id]);

  const replace = (updated: Application) => {
    setApplications(prev => prev.map(a => a.id === updated.id ? updated : a));
  };

  const handleFit = async (application: Application) => {
    const raw = fitDrafts[application.id];
    const score = Number(raw);
    if (!raw || Number.isNaN(score) || score < 0 || score > 10) {
      toast.error('Fit score must be between 0 and 10');
      return;
    }
    setActing(application.id);
    try {
      replace(await marketplaceService.setApplicationFit(application.id, { fit_score: score }));
      toast.success('Fit score saved');
    } catch {
      toast.error('Failed to save fit score');
    } finally {
      setActing(null);
    }
  };

  const handleInvite = async (application: Application) => {
    setActing(application.id);
    try {
      replace(await marketplaceService.inviteCandidate(application.id));
      toast.success('Interview invitation sent');
    } catch {
      toast.error('Failed to invite candidate');
    } finally {
      setActing(null);
    }
  };

  const handleOutcome = async (application: Application, outcome: 'hired' | 'rejected') => {
    setActing(application.id);
    try {
      replace(await marketplaceService.setApplicationOutcome(application.id, { outcome }));
      toast.success(outcome === 'hired' ? 'Candidate marked hired' : 'Candidate rejected');
    } catch {
      toast.error('Failed to record outcome');
    } finally {
      setActing(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Applications"
        description="Review applicants, set fit scores, and invite candidates"
      />

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => <CardSkeleton key={i} />)}
        </div>
      ) : applications.length === 0 ? (
        <EmptyState
          icon={<Briefcase className="w-8 h-8" />}
          title="No applications yet"
          description="Applications to your published IT interviews will appear here."
        />
      ) : (
        <div className="space-y-3">
          {applications.map(application => {
            const closed = application.outcome === 'hired' || application.outcome === 'rejected';
            const status = STATUS_LABELS[application.status] || application.status;

            return (
              <Card key={application.id}>
                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-primary">{application.candidate_name}</h3>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-action-primary/10 text-action-primary">
                        {status}
                      </span>
                      {application.fit_score != null && (
                        <span className="text-xs text-secondary">Fit {application.fit_score.toFixed(1)}/10</span>
                      )}
                    </div>
                    <p className="text-sm text-secondary mt-1">{application.candidate_email}</p>
                    <p className="text-sm text-primary mt-2">{application.public_title || 'IT Interview'}</p>
                    {application.fit_summary && (
                      <p className="text-xs text-muted mt-1 line-clamp-2">{application.fit_summary}</p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    {!closed && (
                      <>
                        <div className="flex items-center gap-1">
                          <input
                            type="number"
                            min={0}
                            max={10}
                            step={0.1}
                            value={fitDrafts[application.id] ?? (application.fit_score ?? '')}
                            onChange={e => setFitDrafts(prev => ({ ...prev, [application.id]: e.target.value }))}
                            placeholder="Fit"
                            className="w-20 px-2 py-1.5 text-sm rounded-lg border border-border bg-input text-primary"
                          />
                          <Button size="sm" variant="ghost" loading={acting === application.id}
                            onClick={() => handleFit(application)}>
                            Save
                          </Button>
                        </div>
                        <Button size="sm" loading={acting === application.id}
                          onClick={() => handleInvite(application)}>
                          <Mail className="w-4 h-4 mr-1" /> Invite
                        </Button>
                        <Button size="sm" variant="danger" disabled={acting === application.id}
                          onClick={() => handleOutcome(application, 'rejected')}>
                          <XCircle className="w-4 h-4 mr-1" /> Reject
                        </Button>
                      </>
                    )}
                    {application.outcome === 'hired' && (
                      <span className="inline-flex items-center gap-1 text-sm text-success">
                        <CheckCircle className="w-4 h-4" /> Hired
                      </span>
                    )}
                    {!closed && application.status === 'interview_accepted' && (
                      <Button size="sm" variant="ghost" disabled={acting === application.id}
                        onClick={() => handleOutcome(application, 'hired')}>
                        <CheckCircle className="w-4 h-4 mr-1" /> Hire
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
