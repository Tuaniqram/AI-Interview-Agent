import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { candidateService } from '../../services/candidateService';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Card } from '../../components/shared/Card';
import { StatusBadge } from '../../components/shared/StatusBadge';
import { StatStrip } from '../../components/shared/StatStrip';
import { useToast } from '../../components/shared/Toast';
import type { CandidateInterviewDetail as Detail } from '../../types/candidate';

const label = (s?: string | null) => (s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ') : '—');
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'long', year: 'numeric', hour: 'numeric', minute: '2-digit' });

export default function CandidateInterviewDetail() {
  const { interviewId } = useParams<{ interviewId: string }>();
  const [interview, setInterview] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    if (!interviewId) {
      setLoading(false);
      return;
    }
    candidateService.getInterviewDetail(interviewId)
      .then(setInterview)
      .catch(() => toast.error('Could not load this interview. Reload the page to try again.'))
      .finally(() => setLoading(false));
  }, [interviewId]);

  if (loading) return <ContentSkeleton />;
  if (!interview) {
    return (
      <Card>
        <EmptyState
          title="Interview not found"
          description="It may have been removed, or the link is incomplete."
          action={<Link to="/candidate/interviews" className="text-[13px] font-medium text-action-primary hover:underline">Back to my interviews</Link>}
        />
      </Card>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      <Link to="/candidate/interviews" className="inline-flex items-center gap-1.5 text-[13px] text-secondary hover:text-primary">
        <ArrowLeft className="w-3.5 h-3.5" /> My interviews
      </Link>

      <div>
        <div className="flex items-center gap-2.5 flex-wrap">
          <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-primary">{interview.job_role}</h1>
          {interview.status && <StatusBadge status={interview.status} />}
        </div>
        <p className="mt-1 text-sm text-secondary">
          {[interview.org_name, interview.started_at && when(interview.started_at)].filter(Boolean).join(' / ')}
        </p>
      </div>

      <StatStrip stats={[
        { label: 'Score', value: interview.final_score != null ? String(interview.final_score) : '—', hint: interview.final_score != null ? '/ 10' : undefined },
        { label: 'Type', value: label(interview.session_type) },
        { label: 'Status', value: label(interview.status) },
      ]} />

      {interview.final_feedback ? (
        <Card padding="lg">
          <h2 className="text-sm font-semibold text-primary mb-2">Feedback</h2>
          <p className="text-sm text-secondary leading-relaxed whitespace-pre-wrap max-w-[70ch]">{interview.final_feedback}</p>
        </Card>
      ) : (
        <p className="text-[13px] text-tertiary">Feedback appears here once the interview has been scored.</p>
      )}

      {interview.ended_at && (
        <p className="text-xs text-tertiary">Finished {when(interview.ended_at)}</p>
      )}
    </div>
  );
}
