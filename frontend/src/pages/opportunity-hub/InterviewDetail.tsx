import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { marketplaceService } from '../../services/marketplaceService';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Button } from '../../components/shared/Button';
import { Input } from '../../components/shared/Input';
import { useToast } from '../../components/shared/Toast';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { ArrowLeft, Building2, Clock, Tag, Shield, Briefcase, Upload, CheckCircle } from 'lucide-react';
import type { PublicInterview } from '../../types/marketplace';

const MAX_CV_BYTES = 5 * 1024 * 1024;

export default function InterviewDetail() {
  const { interviewId } = useParams<{ interviewId: string }>();
  const { candidate, isLoading: authLoading } = useCandidateAuth();
  const [interview, setInterview] = useState<PublicInterview | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [applied, setApplied] = useState(false);
  const [error, setError] = useState('');
  const [accountExists, setAccountExists] = useState(false);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const cvInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  // A logged-in candidate is identified by their token; guests type their details.
  const isLoggedIn = !!candidate;
  const hasProfileCv = !!candidate?.resume_url;
  const cvRequired = !hasProfileCv;

  useEffect(() => {
    if (!interviewId) return;
    setLoading(true);
    marketplaceService.getInterview(interviewId)
      .then(setInterview)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [interviewId]);

  useEffect(() => {
    if (candidate) {
      setName(candidate.name);
      setEmail(candidate.email);
    }
  }, [candidate]);

  const pickCv = (file: File | null) => {
    setError('');
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('CV must be a PDF file');
        return;
      }
      if (file.size > MAX_CV_BYTES) {
        setError('CV is too large (max 5 MB)');
        return;
      }
    }
    setCvFile(file);
  };

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!interviewId) return;
    setError('');
    setAccountExists(false);
    if (cvRequired && !cvFile) {
      setError('Please upload your CV (PDF) to apply');
      return;
    }
    setSubmitting(true);
    try {
      await marketplaceService.applyToInterview(interviewId, {
        ...(isLoggedIn ? {} : { candidate_name: name, candidate_email: email }),
        ...(cvFile ? { resume: cvFile } : {}),
      });
      setApplied(true);
      toast.success('Application submitted');
    } catch (err: any) {
      if (err?.response?.status === 409) setAccountExists(true);
      setError(err?.response?.data?.detail || 'Failed to submit application');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <ContentSkeleton />;
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
          <p className="text-sm text-secondary mb-6">Submit your application with your CV. The organization will review it and invite you to interview.</p>
          {authLoading ? (
            <ContentSkeleton />
          ) : applied ? (
            <div className="rounded-lg bg-green-500/10 p-4 text-sm text-green-700 border border-green-500/20 space-y-2" role="status">
              <p className="flex items-center gap-2 font-semibold">
                <CheckCircle className="w-4 h-4" /> Application submitted
              </p>
              {isLoggedIn ? (
                <p>
                  Check your email for updates.{' '}
                  {candidate?.is_verified ? (
                    <>Track your status in <Link to="/candidate/applications" className="font-medium underline">My Applications</Link>.</>
                  ) : (
                    <>Verify your email to see your applications in <Link to="/candidate/applications" className="font-medium underline">My Applications</Link>.</>
                  )}
                </p>
              ) : (
                <p>
                  Check your email ({email}) for updates. If the organization invites you, the interview link will be sent there.
                  Want to keep your history? <Link to="/candidate/register" className="font-medium underline">Create an account</Link> with the same email.
                </p>
              )}
            </div>
          ) : (
          <form onSubmit={handleApply} className="space-y-4 max-w-md">
            {error && (
              <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 border border-red-500/20" role="alert">
                {error}
                {accountExists && (
                  <> <Link to="/candidate/login" className="font-medium underline">Sign in</Link></>
                )}
              </div>
            )}
            <Input label="Your Name" value={name} onChange={(e) => setName(e.target.value)} required readOnly={isLoggedIn} placeholder="John Doe" />
            <Input label="Email Address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required readOnly={isLoggedIn} placeholder="john@example.com" />
            <div>
              <label className="block text-sm font-medium text-primary mb-1">
                CV (PDF){cvRequired ? ' *' : ''}
              </label>
              <input ref={cvInputRef} type="file" accept=".pdf,application/pdf" onChange={(e) => pickCv(e.target.files?.[0] ?? null)} className="hidden" />
              {hasProfileCv && !cvFile && (
                <p className="text-sm text-secondary mb-2">We'll use the CV on your profile. Upload a new one to replace it.</p>
              )}
              <button type="button" onClick={() => cvInputRef.current?.click()}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-secondary bg-input rounded-lg border border-border hover:border-action-primary/40 transition-colors">
                <Upload className="w-4 h-4" />
                {cvFile ? cvFile.name : hasProfileCv ? 'Upload a different CV' : 'Upload CV'}
              </button>
              {cvFile && (
                <button type="button" onClick={() => { setCvFile(null); if (cvInputRef.current) cvInputRef.current.value = ''; }}
                  className="ml-2 text-xs text-red-500 hover:text-red-600">Remove</button>
              )}
              <p className="text-xs text-muted mt-1">PDF only, up to 5 MB.</p>
            </div>
            <Button type="submit" loading={submitting} className="w-full sm:w-auto">
              Submit application
            </Button>
          </form>
          )}
        </div>
      )}
    </div>
  );
}
