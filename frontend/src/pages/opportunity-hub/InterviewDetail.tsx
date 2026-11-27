import { useEffect, useState, useRef } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import { marketplaceService } from '../../services/marketplaceService';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Button } from '../../components/shared/Button';
import { Input } from '../../components/shared/Input';
import { useToast } from '../../components/shared/Toast';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { FileText, CheckCircle2, X } from 'lucide-react';
import { HubBanner, HubBody } from '../../components/opportunity-hub/HubBanner';
import { closingInfo, formatDate, modeLabel, splitSkills } from '../../components/opportunity-hub/listing';
import type { PublicInterview } from '../../types/marketplace';

const MAX_CV_BYTES = 5 * 1024 * 1024;

export default function InterviewDetail() {
  const { interviewId } = useParams<{ interviewId: string }>();
  // Set by the organization page's links. Without it (a shared link), go back to the hub list:
  // the organization's address can't be rebuilt from its name.
  const backState = useLocation().state as { from?: string; orgName?: string } | null;
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
      .catch(() => setInterview(null))
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
        setError('Your CV needs to be a PDF.');
        return;
      }
      if (file.size > MAX_CV_BYTES) {
        setError('That file is over 5 MB. Try a smaller PDF.');
        return;
      }
    }
    setCvFile(file);
  };

  const clearCv = () => {
    setCvFile(null);
    if (cvInputRef.current) cvInputRef.current.value = '';
  };

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!interviewId) return;
    setError('');
    setAccountExists(false);
    if (cvRequired && !cvFile) {
      setError('Add your CV (PDF) to apply.');
      return;
    }
    setSubmitting(true);
    try {
      await marketplaceService.applyToInterview(interviewId, {
        ...(isLoggedIn ? {} : { candidate_name: name, candidate_email: email }),
        ...(cvFile ? { resume: cvFile } : {}),
      });
      setApplied(true);
      toast.success('Application sent');
    } catch (err: any) {
      if (err?.response?.status === 409) setAccountExists(true);
      setError(err?.response?.data?.detail || 'Could not send the application. Try again in a moment.');
    } finally {
      setSubmitting(false);
    }
  };

  const back = { to: backState?.from || '/opportunity-hub', label: backState?.orgName || 'All organizations' };

  if (loading) return <HubBody><ContentSkeleton /></HubBody>;
  if (!interview) {
    return (
      <>
        <HubBanner back={back} title="Role not found" />
        <HubBody>
          <div className="rounded-xl border border-border bg-section">
            <EmptyState title="Nothing to show" description="It may have closed, or the link is out of date." />
          </div>
        </HubBody>
      </>
    );
  }

  const skills = splitSkills(interview.skills_required);
  const closing = closingInfo(interview.expires_at);
  const isExpired = closing?.tone === 'closed';
  const about = interview.rich_description || interview.description;

  const facts: { label: string; value: string; tone?: string }[] = [
    { label: 'Interview', value: modeLabel(interview.interview_mode) },
    ...(interview.starts_at ? [{ label: 'Opens', value: formatDate(interview.starts_at) }] : []),
    ...(interview.expires_at ? [{
      label: 'Closes',
      value: closing?.tone === 'neutral' ? formatDate(interview.expires_at) : `${formatDate(interview.expires_at)} (${closing?.text.toLowerCase()})`,
      tone: closing?.tone === 'soon' ? 'text-[#f5d58a]' : closing?.tone === 'closed' ? 'text-[#f4a9a0]' : undefined,
    }] : []),
  ];

  return (
    <>
      <HubBanner back={back} eyebrow={interview.org_name} title={interview.title}>
        <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2 text-[13px]">
          {facts.map(f => (
            <div key={f.label}>
              <dt className="text-white/60">{f.label}</dt>
              <dd className={`text-white tabular ${f.tone ?? ''}`}>{f.value}</dd>
            </div>
          ))}
        </dl>
      </HubBanner>

      <HubBody>
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-start">
        <article className="min-w-0">
          {skills.length > 0 && (
            <section className="mb-8" aria-labelledby="skills-heading">
              <h2 id="skills-heading" className="text-sm font-semibold text-primary mb-2.5">Skills they are looking for</h2>
              <ul className="flex flex-wrap gap-1.5">
                {skills.map(s => (
                  <li key={s} className="text-xs h-6 px-2 inline-flex items-center rounded-md border border-border bg-section text-secondary">{s}</li>
                ))}
              </ul>
            </section>
          )}

          <section aria-labelledby="about-heading">
            <h2 id="about-heading" className="text-sm font-semibold text-primary mb-2.5">About the role</h2>
            {about ? (
              <div className="text-sm text-secondary leading-relaxed whitespace-pre-line max-w-[68ch]">{about}</div>
            ) : (
              <p className="text-sm text-tertiary">The organization has not added a description.</p>
            )}
          </section>
        </article>

        <aside className="lg:sticky lg:top-20 rounded-xl border border-border bg-section p-5" aria-labelledby="apply-heading">
          {isExpired ? (
            <>
              <h2 id="apply-heading" className="text-sm font-semibold text-primary">Applications are closed</h2>
              <p className="text-[13px] text-secondary mt-1">This role stopped taking applications on {formatDate(interview.expires_at!)}.</p>
            </>
          ) : authLoading ? (
            <ContentSkeleton />
          ) : applied ? (
            <div role="status">
              <h2 id="apply-heading" className="flex items-center gap-2 text-sm font-semibold text-primary">
                <CheckCircle2 className="w-4 h-4 text-success-text" /> Application sent
              </h2>
              {isLoggedIn ? (
                <p className="text-[13px] text-secondary mt-2">
                  We'll email you with updates.{' '}
                  {candidate?.is_verified ? (
                    <>You can follow it in <Link to="/candidate/applications" className="text-action-primary hover:underline">Applications</Link>.</>
                  ) : (
                    <>Verify your email to follow it in <Link to="/candidate/applications" className="text-action-primary hover:underline">Applications</Link>.</>
                  )}
                </p>
              ) : (
                <>
                  <p className="text-[13px] text-secondary mt-2">
                    Updates go to {email}. If the organization invites you, the interview link arrives there too.
                  </p>
                  <p className="text-[13px] text-secondary mt-2">
                    To keep a history of your applications, <Link to="/candidate/register" className="text-action-primary hover:underline">create an account</Link> with the same email.
                  </p>
                </>
              )}
            </div>
          ) : (
            <form onSubmit={handleApply} className="space-y-4">
              <div>
                <h2 id="apply-heading" className="text-sm font-semibold text-primary">Apply</h2>
                <p className="text-[13px] text-secondary mt-1">The organization reads your CV first. If they invite you, you take the interview by email link.</p>
              </div>

              {error && (
                <div className="rounded-md bg-error-bg px-3 py-2 text-[13px] text-error-text" role="alert">
                  {error}
                  {accountExists && <> <Link to="/candidate/login" className="font-medium underline">Sign in</Link></>}
                </div>
              )}

              <Input label="Your name" value={name} onChange={e => setName(e.target.value)} required readOnly={isLoggedIn} autoComplete="name" />
              <Input label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} required readOnly={isLoggedIn} autoComplete="email" />

              <div className="space-y-1.5">
                <span className="block text-[13px] font-medium text-primary">CV{cvRequired ? '' : ' (optional)'}</span>
                <input ref={cvInputRef} type="file" accept=".pdf,application/pdf" onChange={e => pickCv(e.target.files?.[0] ?? null)} className="sr-only" id="cv-file" />
                {cvFile ? (
                  <div className="flex items-center gap-2 h-9 px-2.5 rounded-md border border-border bg-subtle text-[13px]">
                    <FileText className="w-4 h-4 text-tertiary shrink-0" />
                    <span className="flex-1 min-w-0 truncate text-primary">{cvFile.name}</span>
                    <button type="button" onClick={clearCv} className="p-1 rounded text-tertiary hover:text-primary hover:bg-hover" aria-label="Remove this CV">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <label
                    htmlFor="cv-file"
                    className="flex items-center gap-2 h-9 px-2.5 rounded-md border border-dashed border-[var(--border-strong)] text-[13px] text-secondary hover:text-primary hover:border-[var(--text-tertiary)] cursor-pointer focus-within:ring-[3px] focus-within:ring-[var(--focus-ring)]"
                  >
                    <FileText className="w-4 h-4 text-tertiary" />
                    {hasProfileCv ? 'Use a different CV' : 'Choose a PDF'}
                  </label>
                )}
                <p className="text-xs text-tertiary">
                  {hasProfileCv && !cvFile ? 'The CV on your profile is sent unless you choose another. ' : ''}PDF, up to 5 MB.
                </p>
              </div>

              <Button type="submit" loading={submitting} className="w-full">Send application</Button>

              {!isLoggedIn && (
                <p className="text-xs text-tertiary">
                  Have an account? <Link to="/candidate/login" className="text-action-primary hover:underline">Sign in</Link> to apply with your profile.
                </p>
              )}
            </form>
          )}
        </aside>
      </div>
      </HubBody>
    </>
  );
}
