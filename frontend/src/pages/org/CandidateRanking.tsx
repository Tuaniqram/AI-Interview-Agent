import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOrg } from '../../contexts/OrgContext';
import { apiClient } from '../../services/apiClient';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { useToast } from '../../components/shared/Toast';
import { Trophy, Search } from 'lucide-react';
import { ScoreDisplay } from '../../components/shared/ScoreDisplay';

interface CandidateRank {
  rank: number;
  session_id: string;
  candidate_id: string | null;
  candidate_name: string;
  candidate_email: string | null;
  skills: string | null;
  job_role: string;
  department_name: string | null;
  department_id: number | null;
  final_score: number | null;
  started_at: string | null;
  ended_at: string | null;
}

interface RankingSummary {
  job_role: string;
  department_id: number | null;
  department_name: string | null;
  total_candidates: number;
  average_score: number | null;
  max_score: number | null;
  min_score: number | null;
}

export default function CandidateRanking() {
  const { activeOrg } = useOrg();
  const navigate = useNavigate();
  const toast = useToast();
  const [rankings, setRankings] = useState<CandidateRank[]>([]);
  const [summary, setSummary] = useState<RankingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedRole, setSelectedRole] = useState<string>('');

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    Promise.all([
      apiClient.get<CandidateRank[]>(`/api/v1/orgs/${activeOrg.id}/candidates/ranking`),
      apiClient.get<RankingSummary[]>(`/api/v1/orgs/${activeOrg.id}/candidates/ranking/summary`),
    ]).then(([r, s]) => {
      setRankings(r);
      setSummary(s);
    }).catch(() => toast.error('Failed to load rankings'))
    .finally(() => setLoading(false));
  }, [activeOrg?.id]);

  const filtered = rankings.filter(r => {
    if (search && !r.candidate_name.toLowerCase().includes(search.toLowerCase())) return false;
    if (selectedRole && r.job_role !== selectedRole) return false;
    return true;
  });

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <PageHeader title="Candidate Rankings" description="Ranked interview results across your organization" />

      {/* Summary Cards */}
      {summary.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {summary.map(s => (
            <Card key={`${s.job_role}-${s.department_id}`} padding="lg">
              <h3 className="text-sm font-semibold text-primary">{s.job_role}</h3>
              {s.department_name && <p className="text-xs text-muted">{s.department_name}</p>}
              <div className="flex items-center gap-4 mt-3">
                <div className="text-center">
                  <p className="text-xs text-muted">Candidates</p>
                  <p className="text-lg font-bold text-primary">{s.total_candidates}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted">Avg Score</p>
                  <p className="text-lg font-bold text-action-primary">{s.average_score?.toFixed(1) ?? '—'}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted">Top Score</p>
                  <p className="text-lg font-bold text-success">{s.max_score?.toFixed(1) ?? '—'}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm bg-input text-primary rounded-lg border border-border" placeholder="Search candidates..." />
        </div>
        <select value={selectedRole} onChange={(e) => setSelectedRole(e.target.value)}
          className="px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border">
          <option value="">All Roles</option>
          {[...new Set(rankings.map(r => r.job_role))].map(role => (
            <option key={role} value={role}>{role}</option>
          ))}
        </select>
      </div>

      {/* Ranking List */}
      {filtered.length === 0 ? (
        <EmptyState title="No completed interviews" description="Completed interviews with scores will appear here" />
      ) : (
        <div className="space-y-2">
          {filtered.map(r => (
            <div key={r.session_id}
              className="flex items-center gap-4 p-4 rounded-xl bg-section border border-border hover:border-action-primary/40 transition-colors cursor-pointer"
              onClick={() => navigate(`/interview/${r.session_id}/report`)}>
              {/* Rank Badge */}
              <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                r.rank === 1 ? 'bg-amber-500/20 text-amber-500' :
                r.rank === 2 ? 'bg-slate-400/20 text-slate-400' :
                r.rank === 3 ? 'bg-orange-600/20 text-orange-600' :
                'bg-hover text-muted'
              }`}>
                {r.rank <= 3 ? <Trophy className="w-5 h-5" /> : <span className="font-bold text-sm">{r.rank}</span>}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-primary truncate">{r.candidate_name}</span>
                  {r.job_role && <span className="text-xs px-2 py-0.5 rounded-full bg-action-primary/10 text-action-primary">{r.job_role}</span>}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  {r.department_name && <span className="text-xs text-muted">{r.department_name}</span>}
                  {r.candidate_email && <span className="text-xs text-muted">• {r.candidate_email}</span>}
                </div>
                {r.skills && (
                  <div className="flex gap-1 mt-1.5">
                    {r.skills.split(',').slice(0, 3).map(s => (
                      <span key={s.trim()} className="text-[10px] px-1.5 py-0.5 rounded bg-page text-secondary">{s.trim()}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Score */}
              <div className="shrink-0">
                <ScoreDisplay score={r.final_score} size="sm" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
