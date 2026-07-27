import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { MetricCard } from '../../components/shared/MetricCard';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { useToast } from '../../components/shared/Toast';
import { CompetencyRadar } from '../../components/candidate/CompetencyRadar';
import { CheckCircle, XCircle } from 'lucide-react';
import type { CandidateStats, CandidateInterview, CompetencyScore, SavedListing } from '../../types/candidate';

export default function CandidateDashboard() {
  const { candidate, sendVerification } = useCandidateAuth();
  const [stats, setStats] = useState<CandidateStats | null>(null);
  const [recent, setRecent] = useState<CandidateInterview[]>([]);
  const [competencyScores, setCompetencyScores] = useState<CompetencyScore[]>([]);
  const [savedListings, setSavedListings] = useState<SavedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const toast = useToast();

  useEffect(() => {
    Promise.all([
      candidateService.getStats(),
      candidateService.getInterviews(),
      candidateService.getCompetencyScores(),
      candidateService.getSavedListings().catch(() => []),
    ]).then(([s, i, c, sl]) => {
      setStats(s);
      setRecent(i.slice(0, 5));
      setCompetencyScores(c);
      setSavedListings(sl as SavedListing[]);
    }).catch(() => toast.error('Failed to load dashboard'))
    .finally(() => setLoading(false));
  }, []);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      await sendVerification();
      toast.success('Verification email sent! Check your inbox.');
    } catch {
      toast.error('Failed to send verification. Try again.');
    } finally {
      setVerifying(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      {candidate && !candidate.is_verified && (
        <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200">Verify your email</p>
            <p className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">Some features are locked until you verify your email address.</p>
          </div>
          <button onClick={handleVerify} disabled={verifying} className="shrink-0 px-4 py-2 text-xs font-medium rounded-lg bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 transition-colors">
            {verifying ? 'Sending...' : 'Resend verification'}
          </button>
        </div>
      )}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Welcome, {candidate?.name}</h1>
          <p className="text-[var(--text-secondary)] mt-1">Your interview dashboard</p>
        </div>
        <Link to="/candidate/profile"
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
            candidate?.resume_url
              ? 'text-success border-success/30 bg-success/5'
              : 'text-muted border-border bg-section hover:border-action-primary/40'
          }`}>
          {candidate?.resume_url ? (
            <><CheckCircle className="w-3.5 h-3.5" /> Resume uploaded</>
          ) : (
            <><XCircle className="w-3.5 h-3.5" /> No resume — upload</>
          )}
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Total Interviews" value={stats?.total_interviews ?? 0} />
        <MetricCard label="Completed" value={stats?.completed_interviews ?? 0} />
        <MetricCard label="In Progress" value={stats?.active_interviews ?? 0} />
        <MetricCard label="Avg Score" value={stats?.average_score != null ? `${stats.average_score.toFixed(1)}/10` : '-'} />
      </div>

      {competencyScores.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-1">
            <CompetencyRadar scores={competencyScores} />
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Link to="/candidate/practice" className="p-6 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors">
          <h3 className="font-semibold text-[var(--text-primary)]">Practice Interview</h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1">Create a self-service mock interview to practice</p>
        </Link>
        <Link to="/opportunity-hub" className="p-6 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors">
          <h3 className="font-semibold text-[var(--text-primary)]">Opportunity Hub</h3>
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

      {savedListings.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-3">Saved Opportunities</h2>
          <div className="space-y-2">
            {savedListings.map((listing) => (
              <Link
                key={listing.id}
                to={`/opportunity-hub/interviews/${listing.id}`}
                className="block p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)] hover:border-[var(--action-primary)] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-[var(--text-primary)]">{listing.title}</span>
                    <span className="text-sm text-[var(--text-secondary)] ml-2">@{listing.org_name}</span>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--action-primary)]/10 text-[var(--action-primary)]">
                    {listing.interview_mode}
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
