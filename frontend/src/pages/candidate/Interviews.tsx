import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import type { CandidateInterview } from '../../types/candidate';

export default function CandidateInterviews() {
  const [interviews, setInterviews] = useState<CandidateInterview[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    candidateService.getInterviews()
      .then(setInterviews)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">My Interviews</h1>
        <p className="text-[var(--text-secondary)] mt-1">All interviews you've taken</p>
      </div>

      {interviews.length === 0 ? (
        <EmptyState
          title="No interviews yet"
          description="Take a practice interview or apply to one from the marketplace"
        />
      ) : (
        <div className="space-y-3">
          {interviews.map((interview) => (
            <Link
              key={interview.id}
              to={`/candidate/interviews/${interview.id}`}
              className="block p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-[var(--text-primary)]">{interview.job_role}</h3>
                  {interview.department_name && (
                    <p className="text-sm text-[var(--text-secondary)]">{interview.department_name}</p>
                  )}
                </div>
                <div className="text-right">
                  {interview.final_score != null && (
                    <span className="text-lg font-bold text-[var(--action-primary)]">{interview.final_score}/10</span>
                  )}
                  <div className="text-xs text-[var(--text-secondary)] mt-1">
                    {interview.started_at ? new Date(interview.started_at).toLocaleDateString() : ''}
                  </div>
                </div>
              </div>
              <div className="flex gap-2 mt-2">
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  interview.status === 'completed'
                    ? 'bg-green-100 dark:bg-green-900/20 text-green-600'
                    : interview.status === 'active'
                    ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-600'
                    : 'bg-gray-100 dark:bg-gray-900/20 text-gray-600'
                }`}>
                  {interview.status}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--action-primary)]/10 text-[var(--action-primary)]">
                  {interview.session_type}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
