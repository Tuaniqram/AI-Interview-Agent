import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { marketplaceService } from '../../services/marketplaceService';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { Button } from '../../components/shared/Button';
import { Input } from '../../components/shared/Input';
import { Building2, Clock, Tag } from 'lucide-react';
import type { PublicInterview } from '../../types/marketplace';

export default function InterviewDetail() {
  const { interviewId } = useParams<{ interviewId: string }>();
  const navigate = useNavigate();
  const [interview, setInterview] = useState<PublicInterview | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!interviewId) return;
    setLoading(true);
    marketplaceService.getInterview(interviewId)
      .then(setInterview)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [interviewId]);

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!interviewId) return;
    setError('');
    setStarting(true);
    try {
      const res = await marketplaceService.startInterview(interviewId, {
        candidate_name: name,
        candidate_email: email,
      });
      navigate(`/interview/${res.session_id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to start interview');
    } finally {
      setStarting(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading interview..." />;
  if (!interview) return <EmptyState title="Interview not found" />;

  const skills = interview.skills_required?.split(',').map(s => s.trim()).filter(Boolean) || [];
  const isExpired = interview.expires_at ? new Date(interview.expires_at) < new Date() : false;
  const daysUntil = interview.expires_at
    ? Math.ceil((new Date(interview.expires_at).getTime() - Date.now()) / 86400000)
    : null;

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-start gap-4 mb-2">
          <div className="w-12 h-12 rounded-xl bg-[var(--action-primary)]/10 flex items-center justify-center shrink-0">
            <Building2 className="w-6 h-6 text-[var(--action-primary)]" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">{interview.title}</h1>
            <div className="flex items-center gap-2 mt-1 text-sm text-[var(--text-secondary)]">
              {interview.org_name && <span>{interview.org_name}</span>}
              {interview.department_name && (
                <>
                  <span>·</span>
                  <span>{interview.department_name}</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs px-3 py-1 rounded-full bg-[var(--action-primary)]/10 text-[var(--action-primary)] font-medium">
          {interview.interview_mode}
        </span>
        {skills.map(skill => (
          <span key={skill} className="text-xs px-3 py-1 rounded-full bg-[var(--bg-section)] text-[var(--text-muted)] border border-[var(--border-color)] flex items-center gap-1">
            <Tag className="w-3 h-3" /> {skill}
          </span>
        ))}
        {isExpired ? (
          <span className="text-xs px-3 py-1 rounded-full bg-red-500/15 text-red-500 font-medium">Expired</span>
        ) : daysUntil !== null && daysUntil <= 7 ? (
          <span className="text-xs px-3 py-1 rounded-full bg-yellow-500/15 text-yellow-500 font-medium flex items-center gap-1">
            <Clock className="w-3 h-3" /> Expires in {daysUntil}d
          </span>
        ) : null}
      </div>

      {/* AI-generated description */}
      {interview.rich_description && (
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)]">
          <div className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-line">
            {interview.rich_description}
          </div>
        </div>
      )}

      {/* Short description fallback */}
      {!interview.rich_description && interview.description && (
        <p className="text-[var(--text-secondary)]">{interview.description}</p>
      )}

      {/* Dates */}
      <div className="flex items-center gap-6 text-sm text-[var(--text-muted)]">
        {interview.starts_at && (
          <span className="flex items-center gap-1.5">
            <Clock className="w-4 h-4" /> Opens {new Date(interview.starts_at).toLocaleDateString()}
          </span>
        )}
        {interview.expires_at && (
          <span className="flex items-center gap-1.5">
            <Clock className="w-4 h-4" /> Closes {new Date(interview.expires_at).toLocaleDateString()}
          </span>
        )}
      </div>

      {/* Start form */}
      <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)]">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Apply for this interview</h2>
        <form onSubmit={handleStart} className="space-y-4">
          {error && (
            <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600">{error}</div>
          )}
          <Input label="Your Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <Input label="Email Address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Button type="submit" loading={starting}>
            Start Interview
          </Button>
        </form>
      </div>
    </div>
  );
}
