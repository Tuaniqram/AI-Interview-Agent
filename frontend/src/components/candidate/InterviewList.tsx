import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { StatusBadge } from '../shared/StatusBadge';
import { ScoreDisplay } from '../shared/ScoreDisplay';
import type { CandidateInterview } from '../../types/candidate';

const label = (s?: string | null) => (s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ') : '');

/** A candidate's interviews as one list: role and organization, type, status, score and date per row. */
export function InterviewList({ interviews }: { interviews: CandidateInterview[] }) {
  return (
    <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden">
      {interviews.map(interview => (
        <li key={interview.id}>
          <Link
            to={`/candidate/interviews/${interview.id}`}
            className="group flex items-center gap-4 px-4 py-3 hover:bg-subtle transition-colors"
          >
            <span className="flex-1 min-w-0">
              <span className="block text-sm font-medium text-primary truncate">{interview.job_role}</span>
              <span className="block text-xs text-tertiary truncate">
                {[interview.org_name, label(interview.session_type)].filter(Boolean).join(' / ')}
              </span>
            </span>
            <span className="hidden sm:block">{interview.status && <StatusBadge status={interview.status} />}</span>
            <span className="w-28 hidden md:flex justify-end"><ScoreDisplay score={interview.final_score ?? null} size="inline" /></span>
            <span className="w-24 text-right text-xs text-tertiary tabular hidden sm:block">
              {interview.started_at
                ? new Date(interview.started_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
                : ''}
            </span>
            <ChevronRight className="w-4 h-4 text-tertiary group-hover:text-primary shrink-0" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
