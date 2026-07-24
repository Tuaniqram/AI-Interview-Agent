import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { marketplaceService } from '../../services/marketplaceService';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { Button } from '../../components/shared/Button';
import { Input } from '../../components/shared/Input';
import { ArrowLeft, Building2, Clock, Tag, Shield, Briefcase } from 'lucide-react';
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
      <Link
        to={interview.org_name ? `/opportunity-hub/organizations/${interview.org_name?.toLowerCase().replace(/\s+/g, '-')}` : '/opportunity-hub'}
        className="inline-flex items-center gap-1.5 text-sm text-secondary hover:text-primary transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to opportunities
      </Link>

      <div className="rounded-2xl bg-gradient-to-br from-[#7C3AED]/5 to-[#A78BFA]/5 border border-[#7C3AED]/10 p-6 sm:p-8">
        <div className="flex items-start gap-4 mb-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#A78BFA] flex items-center justify-center shrink-0">
            <Briefcase className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-primary font-heading">{interview.title}</h1>
            <div className="flex items-center gap-2 mt-1 text-sm text-secondary flex-wrap">
              {interview.org_name && (
                <span className="flex items-center gap-1">
                  <Building2 className="w-3.5 h-3.5" />
                  {interview.org_name}
                </span>
              )}
              {interview.department_name && (
                <>
                  <span className="text-muted">·</span>
                  <span>{interview.department_name}</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs px-3 py-1 rounded-full bg-[#7C3AED]/10 text-[#7C3AED] font-medium flex items-center gap-1">
            <Shield className="w-3 h-3" />
            {interview.interview_mode}
          </span>
          {skills.map(skill => (
            <span key={skill} className="text-xs px-3 py-1 rounded-full bg-[var(--bg-section)] text-secondary border border-[var(--border-color)] flex items-center gap-1">
              <Tag className="w-3 h-3" /> {skill}
            </span>
          ))}
          {isExpired ? (
            <span className="text-xs px-3 py-1 rounded-full bg-red-500/15 text-red-500 font-medium">Expired</span>
          ) : daysUntil !== null && daysUntil <= 7 ? (
            <span className="text-xs px-3 py-1 rounded-full bg-amber-500/15 text-amber-500 font-medium flex items-center gap-1">
              <Clock className="w-3 h-3" /> {daysUntil}d left
            </span>
          ) : null}
        </div>
      </div>

      {interview.rich_description && (
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)]">
          <h2 className="text-sm font-semibold text-primary mb-3">About this position</h2>
          <div className="text-sm text-secondary leading-relaxed whitespace-pre-line">
            {interview.rich_description}
          </div>
        </div>
      )}

      {!interview.rich_description && interview.description && (
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)]">
          <h2 className="text-sm font-semibold text-primary mb-3">About this position</h2>
          <p className="text-sm text-secondary">{interview.description}</p>
        </div>
      )}

      {interview.starts_at || interview.expires_at ? (
        <div className="flex items-center gap-6 text-sm text-muted">
          {interview.starts_at && (
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              Opens {new Date(interview.starts_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
          )}
          {interview.expires_at && (
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              Closes {new Date(interview.expires_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
          )}
        </div>
      ) : null}

      {!isExpired && (
        <div className="rounded-xl bg-gradient-to-br from-[#7C3AED]/5 to-[#A78BFA]/5 border border-[#7C3AED]/10 p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-primary mb-1 font-heading">Apply for this interview</h2>
          <p className="text-sm text-secondary mb-6">Enter your details to get started. The interview will begin immediately.</p>
          <form onSubmit={handleStart} className="space-y-4 max-w-md">
            {error && (
              <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 border border-red-500/20">{error}</div>
            )}
            <Input label="Your Name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="John Doe" />
            <Input label="Email Address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="john@example.com" />
            <Button type="submit" loading={starting} className="w-full sm:w-auto">
              Start Interview
            </Button>
          </form>
        </div>
      )}
    </div>
  );
}
