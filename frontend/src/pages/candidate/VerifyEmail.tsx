import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AuthLayout } from '../../components/auth/AuthLayout';
import { Button } from '../../components/shared/Button';
import { candidateService } from '../../services/candidateService';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';

type State = 'verifying' | 'success' | 'error' | 'missing';

/** Target of the verification email link: /candidate/verify?token=... */
export default function CandidateVerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const { isAuthenticated, refreshProfile } = useCandidateAuth();
  const [state, setState] = useState<State>(token ? 'verifying' : 'missing');
  const [error, setError] = useState('');
  const started = useRef(false); // the token is single use: never verify twice (StrictMode)

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    candidateService.verifyEmail(token)
      .then(async () => {
        await refreshProfile(); // clears the "verify your email" banner if signed in here
        setState('success');
      })
      .catch((err: any) => {
        setError(err?.response?.data?.detail || 'This verification link is invalid or has already been used.');
        setState('error');
      });
  }, [token, refreshProfile]);

  return (
    <AuthLayout role="candidate">
      <div className="text-center space-y-4" role="status" aria-live="polite">
        {state === 'verifying' && (
          <>
            <div className="mx-auto animate-spin w-8 h-8 border-2 border-[var(--action-primary)] border-t-transparent rounded-full" />
            <h1 className="text-xl font-bold text-[var(--text-primary)]">Verifying your email…</h1>
          </>
        )}
        {state === 'success' && (
          <>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">Email verified</h1>
            <p className="text-sm text-[var(--text-secondary)]">
              Your applications and interview history are now available.
            </p>
            <Link to={isAuthenticated ? '/candidate/applications' : '/candidate/login'}>
              <Button className="w-full">{isAuthenticated ? 'Go to My Applications' : 'Sign in'}</Button>
            </Link>
          </>
        )}
        {(state === 'error' || state === 'missing') && (
          <>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">Verification failed</h1>
            <p className="text-sm text-[var(--text-secondary)]" role="alert">
              {state === 'missing' ? 'This verification link is missing its token.' : error}
            </p>
            <Link to={isAuthenticated ? '/candidate/dashboard' : '/candidate/login'} className="text-[var(--action-primary)] hover:underline text-sm">
              {isAuthenticated ? 'Back to dashboard to request a new link' : 'Sign in to request a new link'}
            </Link>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
