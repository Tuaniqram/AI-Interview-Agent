import { useCallback, useEffect, useRef, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { marketplaceService } from '../../services/marketplaceService';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { CardSkeleton } from '../../components/shared/Skeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Button } from '../../components/shared/Button';
import { useToast } from '../../components/shared/Toast';
import {
  AlertTriangle, Briefcase, CheckCircle, ChevronDown, ChevronUp, FileText, Loader2, Mail, RefreshCw, XCircle,
} from 'lucide-react';
import type { Application, FitStatus } from '../../types/marketplace';

const STATUS_LABELS: Record<string, string> = {
  applied: 'Applied',
  screening: 'In review',
  evaluated: 'Evaluated',
  interview_offered: 'Invited',
  interview_accepted: 'Accepted',
  interview_declined: 'Declined',
  interviewed: 'Interviewed',
  hired: 'Hired',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
};

const FIT_STATUS_LABELS: Record<FitStatus, string> = {
  pending: 'Evaluation queued…',
  running: 'Evaluating…',
  completed: 'Evaluated',
  failed: 'Evaluation failed',
};

const POLL_INTERVAL_MS = 4000;
const MAX_POLLS = 45; // ~3 minutes, then stop and let the owner re-run
const STALE_AFTER_MS = 10 * 60 * 1000;

const isInFlight = (a: Application) => a.fit_status === 'pending' || a.fit_status === 'running';
const isStale = (a: Application) =>
  isInFlight(a) && !!a.updated_at && Date.now() - new Date(a.updated_at).getTime() > STALE_AFTER_MS;

function scoreTone(score: number): string {
  if (score >= 7) return 'bg-green-500/15 text-green-600';
  if (score >= 4) return 'bg-amber-500/15 text-amber-600';
  return 'bg-red-500/15 text-red-600';
}

function BulletList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <h4 className="text-xs font-semibold text-primary mb-1">{title}</h4>
      <ul className="list-disc pl-4 space-y-0.5 text-xs text-secondary">
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ul>
    </div>
  );
}

function FitBreakdownPanel({ application }: { application: Application }) {
  const bd = application.fit_breakdown;
  if (!bd) return null;
  const org = bd.meta?.org_documents_used;

  return (
    <div className="mt-3 pt-3 border-t border-border grid gap-4 sm:grid-cols-2" data-testid="fit-breakdown">
      {bd.matched_competencies.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-primary mb-1">Matched competencies</h4>
          <ul className="space-y-1 text-xs text-secondary">
            {bd.matched_competencies.map(c => (
              <li key={c.id}>
                <span className="font-medium text-primary">{c.name}</span>
                {c.evidence ? <> — {c.evidence}</> : null}
              </li>
            ))}
          </ul>
        </div>
      )}
      {bd.missing_competencies.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-primary mb-1">Missing or unproven</h4>
          <ul className="space-y-1 text-xs text-secondary">
            {bd.missing_competencies.map(c => (
              <li key={c.id}>
                <span className="font-medium text-primary">{c.name}</span>
                {c.reason ? <> — {c.reason}</> : null}
              </li>
            ))}
          </ul>
        </div>
      )}
      <BulletList title="CV strengths" items={bd.resume_strengths} />
      <BulletList title="Risks" items={bd.risks} />
      <div className="sm:col-span-2">
        <BulletList title="Suggested interview probes" items={bd.recommended_probes} />
      </div>
      <p className="sm:col-span-2 text-[11px] text-muted">
        {org ? `Assessed against ${org} organization document excerpt${org === 1 ? '' : 's'} and the role's competencies.` : "Assessed against the role's competencies (no organization documents were available)."}
      </p>
    </div>
  );
}

export default function OrgApplications() {
  const { activeOrg } = useOrg();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const pollCount = useRef(0);
  const toast = useToast();

  const load = useCallback(async (silent = false) => {
    if (!activeOrg?.id) return;
    if (!silent) setLoading(true);
    try {
      setApplications(await marketplaceService.listOrgApplications(activeOrg.id));
    } catch {
      if (!silent) toast.error('Failed to load applications');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [activeOrg?.id]);

  useEffect(() => {
    pollCount.current = 0;
    load();
  }, [load]);

  // While any evaluation is running, refresh quietly so scores appear without a manual reload.
  const hasInFlight = applications.some(a => isInFlight(a) && !isStale(a));
  useEffect(() => {
    if (!hasInFlight) return;
    const timer = setInterval(() => {
      if (pollCount.current >= MAX_POLLS) {
        clearInterval(timer);
        return;
      }
      pollCount.current += 1;
      load(true);
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [hasInFlight, load]);

  const replace = (updated: Application) => {
    setApplications(prev => prev.map(a => a.id === updated.id ? updated : a));
  };

  const run = async (application: Application, action: () => Promise<void>, failure: string) => {
    setActing(application.id);
    try {
      await action();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || failure);
    } finally {
      setActing(null);
    }
  };

  const handleDownloadCv = (application: Application) =>
    run(application, async () => {
      const blob = await marketplaceService.downloadApplicationResume(application.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = application.resume_filename || `${application.candidate_name}_cv.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }, 'Could not download the CV');

  const handleReevaluate = (application: Application) =>
    run(application, async () => {
      pollCount.current = 0;
      replace(await marketplaceService.evaluateApplication(application.id));
      toast.success('Evaluation started');
    }, 'Could not start the evaluation');

  const handleInvite = (application: Application) =>
    run(application, async () => {
      replace(await marketplaceService.inviteCandidate(application.id));
      toast.success(application.org_decision === 'invited' ? 'Invitation re-sent' : 'Interview invitation sent');
    }, 'Failed to invite candidate');

  const handleOutcome = (application: Application, outcome: 'hired' | 'rejected') =>
    run(application, async () => {
      replace(await marketplaceService.setApplicationOutcome(application.id, { outcome }));
      toast.success(outcome === 'hired' ? 'Candidate marked hired' : 'Candidate rejected');
    }, 'Failed to record outcome');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Applications"
        description="Applicants are evaluated automatically against your role and documents. Review the fit, then decide whom to invite."
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
            const busy = acting === application.id;
            const inFlight = isInFlight(application) && !isStale(application);
            const canRerun = application.has_resume && !inFlight && !closed;
            const showDetails = application.fit_status === 'completed' && !!application.fit_breakdown;
            const open = !!expanded[application.id];

            return (
              <Card key={application.id}>
                <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-primary">{application.candidate_name}</h3>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-action-primary/10 text-action-primary">
                        {status}
                      </span>
                      {application.fit_score != null && application.fit_status === 'completed' && (
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${scoreTone(application.fit_score)}`}>
                          Fit {application.fit_score.toFixed(1)}/10
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-secondary mt-1 break-all">{application.candidate_email}</p>
                    <p className="text-sm text-primary mt-2">{application.public_title || 'IT Interview'}</p>

                    <div className="mt-2 flex items-center gap-2 flex-wrap text-xs" aria-live="polite">
                      {inFlight && (
                        <span className="inline-flex items-center gap-1 text-secondary">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          {FIT_STATUS_LABELS[application.fit_status]}
                        </span>
                      )}
                      {application.fit_status === 'failed' && (
                        <span className="inline-flex items-center gap-1 text-red-600">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          {FIT_STATUS_LABELS.failed} — you can still invite, or re-run it
                        </span>
                      )}
                      {isStale(application) && (
                        <span className="inline-flex items-center gap-1 text-amber-600">
                          <AlertTriangle className="w-3.5 h-3.5" /> Evaluation seems stuck — re-run it
                        </span>
                      )}
                    </div>

                    {application.fit_summary && application.fit_status === 'completed' && (
                      <p className={`text-sm text-secondary mt-2 ${open ? '' : 'line-clamp-2'}`}>
                        {application.fit_summary}
                      </p>
                    )}
                    {showDetails && (
                      <button
                        type="button"
                        onClick={() => setExpanded(prev => ({ ...prev, [application.id]: !prev[application.id] }))}
                        aria-expanded={open}
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-action-primary hover:underline"
                      >
                        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        {open ? 'Hide fit details' : 'Show fit details'}
                      </button>
                    )}
                    {showDetails && open && <FitBreakdownPanel application={application} />}
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    {application.has_resume ? (
                      <Button size="sm" variant="outline" loading={busy} onClick={() => handleDownloadCv(application)}
                        title={application.resume_filename || 'Download CV'}>
                        <FileText className="w-4 h-4 mr-1" /> CV
                      </Button>
                    ) : (
                      <span className="text-xs text-muted">No CV</span>
                    )}
                    {canRerun && (
                      <Button size="sm" variant="ghost" disabled={busy} onClick={() => handleReevaluate(application)}>
                        <RefreshCw className="w-4 h-4 mr-1" />
                        {application.fit_status === 'failed' ? 'Re-run evaluation' : 'Re-evaluate'}
                      </Button>
                    )}
                    {!closed && application.org_decision !== 'invited' && (
                      <Button size="sm" disabled={busy} onClick={() => handleInvite(application)}>
                        <Mail className="w-4 h-4 mr-1" /> Invite
                      </Button>
                    )}
                    {!closed && application.org_decision === 'invited' && application.status === 'interview_offered' && (
                      <>
                        <span className="text-xs text-secondary">Invitation sent — awaiting reply</span>
                        <Button size="sm" variant="ghost" disabled={busy} onClick={() => handleInvite(application)}>
                          <Mail className="w-4 h-4 mr-1" /> Resend
                        </Button>
                      </>
                    )}
                    {!closed && (
                      <Button size="sm" variant="danger" disabled={busy} onClick={() => handleOutcome(application, 'rejected')}>
                        <XCircle className="w-4 h-4 mr-1" /> Reject
                      </Button>
                    )}
                    {application.outcome === 'hired' && (
                      <span className="inline-flex items-center gap-1 text-sm text-success">
                        <CheckCircle className="w-4 h-4" /> Hired
                      </span>
                    )}
                    {application.outcome === 'rejected' && (
                      <span className="text-sm text-secondary">Rejected</span>
                    )}
                    {!closed && application.status === 'interview_accepted' && (
                      <Button size="sm" variant="ghost" disabled={busy} onClick={() => handleOutcome(application, 'hired')}>
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
