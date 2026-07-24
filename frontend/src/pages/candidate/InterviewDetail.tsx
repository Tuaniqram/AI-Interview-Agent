import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import type { CandidateInterviewDetail as Detail } from '../../types/candidate';

export default function CandidateInterviewDetail() {
  const { interviewId } = useParams<{ interviewId: string }>();
  const [interview, setInterview] = useState<Detail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!interviewId) return;
    candidateService.getInterviewDetail(interviewId)
      .then(setInterview)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [interviewId]);

  if (loading) return <LoadingSpinner />;
  if (!interview) return <EmptyState title="Interview not found" />;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">{interview.job_role}</h1>
        {interview.department_name && (
          <p className="text-[var(--text-secondary)]">{interview.department_name}</p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)]">
          <div className="text-sm text-[var(--text-secondary)]">Status</div>
          <div className="text-lg font-semibold text-[var(--text-primary)] capitalize">{interview.status}</div>
        </div>
        <div className="p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)]">
          <div className="text-sm text-[var(--text-secondary)]">Type</div>
          <div className="text-lg font-semibold text-[var(--text-primary)] capitalize">{interview.session_type}</div>
        </div>
        <div className="p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)]">
          <div className="text-sm text-[var(--text-secondary)]">Score</div>
          <div className="text-lg font-semibold text-[var(--action-primary)]">
            {interview.final_score != null ? `${interview.final_score}/10` : '-'}
          </div>
        </div>
      </div>

      {interview.final_feedback && (
        <div className="p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)]">
          <h2 className="font-semibold text-[var(--text-primary)] mb-2">Feedback</h2>
          <p className="text-sm text-[var(--text-secondary)] whitespace-pre-wrap">{interview.final_feedback}</p>
        </div>
      )}

      {interview.started_at && (
        <p className="text-sm text-[var(--text-secondary)]">
          Taken on {new Date(interview.started_at).toLocaleString()}
          {interview.ended_at && ` - Completed ${new Date(interview.ended_at).toLocaleString()}`}
        </p>
      )}
    </div>
  );
}
