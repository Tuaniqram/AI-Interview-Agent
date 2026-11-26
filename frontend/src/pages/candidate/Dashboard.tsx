import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { candidateService } from '../../services/candidateService';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { StatStrip } from '../../components/shared/StatStrip';
import { Card } from '../../components/shared/Card';
import { Button } from '../../components/shared/Button';
import { useToast } from '../../components/shared/Toast';
import { InterviewList } from '../../components/candidate/InterviewList';
import { AlertCircle, ChevronRight, FileText, PlayCircle, Store } from 'lucide-react';
import type { CandidateStats, CandidateInterview, CompetencyScore, SavedListing } from '../../types/candidate';

function barTone(score: number): string {
  if (score >= 7) return 'bg-success';
  if (score >= 5) return 'bg-warning';
  return 'bg-error';
}

/** One row per skill: the average score across your interviews, and how many answers it comes from. */
function SkillList({ scores }: { scores: CompetencyScore[] }) {
  return (
    <ul className="grid gap-x-10 gap-y-4 sm:grid-cols-2">
      {scores.map(s => (
        <li key={s.competency || s.name}>
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[13px] text-primary truncate">{s.name}</span>
            <span className="text-[13px] font-semibold text-primary tabular">{s.average_score.toFixed(1)}</span>
          </div>
          <div className="mt-1.5 flex items-center gap-3">
            <div className="flex-1 h-1.5 rounded-full bg-hover overflow-hidden" aria-hidden>
              <div className={`h-full rounded-full ${barTone(s.average_score)}`} style={{ width: `${Math.max(0, Math.min(100, s.average_score * 10))}%` }} />
            </div>
            <span className="text-xs text-tertiary w-20 text-right tabular">
              {s.evidence_count} {s.evidence_count === 1 ? 'answer' : 'answers'}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

const NEXT = [
  { to: '/candidate/practice', icon: PlayCircle, title: 'Practice interview', text: 'A mock interview for any role, as often as you like' },
  { to: '/opportunity-hub', icon: Store, title: 'Find open interviews', text: 'Roles from organizations hiring now' },
  { to: '/candidate/profile', icon: FileText, title: 'Your profile and CV', text: 'Skills from your CV shape your interviews' },
];

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
    }).catch((err) => {
      // 403 = email not verified: the verify banner above already explains it, so no error toast.
      if (err?.response?.status !== 403) toast.error('Could not load your dashboard. Reload the page to try again.');
    })
    .finally(() => setLoading(false));
  }, []);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      await sendVerification();
      toast.success('Verification email sent. Check your inbox.');
    } catch {
      toast.error('Could not send the verification email. Try again in a minute.');
    } finally {
      setVerifying(false);
    }
  };

  if (loading) return <ContentSkeleton />;

  const skills = [...competencyScores].sort((a, b) => b.evidence_count - a.evidence_count || b.average_score - a.average_score);

  return (
    <div className="space-y-8">
      {candidate && !candidate.is_verified && (
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 rounded-xl bg-warning-bg px-4 py-3" role="status">
          <AlertCircle className="w-4 h-4 text-warning-text shrink-0 hidden sm:block" />
          <div className="flex-1">
            <p className="text-sm font-medium text-warning-text">Verify your email</p>
            <p className="text-[13px] text-warning-text/80 mt-0.5">Your applications and scores stay hidden until you confirm your email address.</p>
          </div>
          <Button size="sm" variant="secondary" loading={verifying} onClick={handleVerify}>Resend verification</Button>
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-primary">Welcome back, {candidate?.name}</h1>
          <p className="text-sm text-secondary mt-1">Your interviews, scores and the skills they show.</p>
        </div>
        <Link
          to="/candidate/profile"
          className={`inline-flex items-center gap-1.5 h-8 px-3 rounded-md text-[13px] font-medium border transition-colors self-start sm:self-auto ${
            candidate?.resume_url
              ? 'border-transparent bg-success-bg text-success-text'
              : 'border-border-strong text-primary hover:bg-hover'
          }`}
        >
          <FileText className="w-4 h-4" />
          {candidate?.resume_url ? 'CV on file' : 'Upload your CV'}
        </Link>
      </div>

      <StatStrip stats={[
        { label: 'Interviews', value: String(stats?.total_interviews ?? 0), to: '/candidate/interviews' },
        { label: 'Completed', value: String(stats?.completed_interviews ?? 0) },
        { label: 'In progress', value: String(stats?.active_interviews ?? 0) },
        { label: 'Average score', value: stats?.average_score != null ? stats.average_score.toFixed(1) : '—', hint: stats?.average_score != null ? '/ 10' : undefined },
      ]} />

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2 min-w-0" aria-labelledby="skills-heading">
          <h2 id="skills-heading" className="text-sm font-semibold text-primary mb-3">Your skills</h2>
          {skills.length > 0 ? (
            <Card padding="lg">
              <SkillList scores={skills.slice(0, 8)} />
            </Card>
          ) : (
            <Card padding="lg">
              <p className="text-sm font-medium text-primary">No scores yet</p>
              <p className="text-[13px] text-secondary mt-1">
                {candidate && !candidate.is_verified
                  ? 'Verify your email, then complete an interview to see your skills here.'
                  : 'Complete a practice or real interview and your skills show up here.'}
              </p>
              <Link to="/candidate/practice" className="inline-block mt-3 text-[13px] font-medium text-action-primary hover:underline">Start a practice interview</Link>
            </Card>
          )}
        </section>

        <section aria-labelledby="next-heading">
          <h2 id="next-heading" className="text-sm font-semibold text-primary mb-3">Next steps</h2>
          <Card padding="none">
            <ul className="divide-y divide-[var(--divider)]">
              {NEXT.map(({ to, icon: Icon, title, text }) => (
                <li key={to}>
                  <Link to={to} className="group flex items-center gap-3 px-4 py-3 hover:bg-subtle transition-colors">
                    <span className="w-8 h-8 rounded-lg border border-border bg-subtle flex items-center justify-center text-secondary shrink-0">
                      <Icon className="w-4 h-4" />
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className="block text-[13px] font-medium text-primary">{title}</span>
                      <span className="block text-xs text-tertiary">{text}</span>
                    </span>
                    <ChevronRight className="w-4 h-4 text-tertiary group-hover:text-primary" />
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      </div>

      {recent.length > 0 && (
        <section aria-labelledby="recent-heading">
          <div className="flex items-center justify-between mb-3">
            <h2 id="recent-heading" className="text-sm font-semibold text-primary">Recent interviews</h2>
            <Link to="/candidate/interviews" className="text-[13px] text-secondary hover:text-primary">View all</Link>
          </div>
          <InterviewList interviews={recent} />
        </section>
      )}

      {savedListings.length > 0 && (
        <section aria-labelledby="saved-heading">
          <h2 id="saved-heading" className="text-sm font-semibold text-primary mb-3">Saved opportunities</h2>
          <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden">
            {savedListings.map(listing => (
              <li key={listing.id}>
                <Link to={`/opportunity-hub/interviews/${listing.id}`} className="group flex items-center gap-4 px-4 py-3 hover:bg-subtle transition-colors">
                  <span className="flex-1 min-w-0">
                    <span className="block text-sm font-medium text-primary truncate">{listing.title}</span>
                    <span className="block text-xs text-tertiary truncate">{listing.org_name}</span>
                  </span>
                  <span className="text-xs text-secondary capitalize">{listing.interview_mode}</span>
                  <ChevronRight className="w-4 h-4 text-tertiary group-hover:text-primary" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
