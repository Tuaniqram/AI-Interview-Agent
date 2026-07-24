import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { MetricCard } from '../../components/shared/MetricCard';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import type { CandidateStats, CandidateInterview } from '../../types/candidate';

export default function CandidateDashboard() {
  const { candidate } = useCandidateAuth();
  const [stats, setStats] = useState<CandidateStats | null>(null);
  const [recent, setRecent] = useState<CandidateInterview[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      candidateService.getStats(),
      candidateService.getInterviews(),
    ]).then(([s, i]) => {
      setStats(s);
      setRecent(i.slice(0, 5));
    }).catch(console.error)
    .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Welcome, {candidate?.name}</h1>
        <p className="text-[var(--text-secondary)] mt-1">Your interview dashboard</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Total Interviews" value={stats?.total_interviews ?? 0} />
        <MetricCard label="Completed" value={stats?.completed_interviews ?? 0} />
        <MetricCard label="In Progress" value={stats?.active_interviews ?? 0} />
        <MetricCard label="Avg Score" value={stats?.average_score != null ? `${stats.average_score.toFixed(1)}/10` : '-'} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link to="/candidate/practice" className="p-6 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors">
          <h3 className="font-semibold text-[var(--text-primary)]">Practice Interview</h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Create a self-service mock interview to practice</p>
        </Link>
        <Link to="/marketplace" className="p-6 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors">
          <h3 className="font-semibold text-[var(--text-primary)]">Browse Marketplace</h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Find open interviews from companies</p>
        </Link>
      </div>

      {recent.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Recent Interviews</h2>
          <div className="space-y-2">
            {recent.map((interview) => (
              <Link
                key={interview.id}
                to={`/candidate/interviews/${interview.id}`}
                className="block p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-[var(--text-primary)]">{interview.job_role}</span>
                    {interview.department_name && (
                      <span className="text-sm text-[var(--text-secondary)] ml-2">@{interview.department_name}</span>
                    )}
                  </div>
                  {interview.final_score != null && (
                    <span className="text-sm font-medium text-[var(--action-primary)]">{interview.final_score}/10</span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--action-primary)]/10 text-[var(--action-primary)]">
                    {interview.session_type}
                  </span>
                  <span className="text-xs text-[var(--text-secondary)]">
                    {interview.started_at ? new Date(interview.started_at).toLocaleDateString() : ''}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
