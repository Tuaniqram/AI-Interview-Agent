import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AuthLayout } from '../../components/auth/AuthLayout';
import { Input } from '../../components/shared/Input';
import { Button } from '../../components/shared/Button';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';

/**
 * Target of the "finish setting up your account" email: /candidate/claim?token=...
 * Reaching this page proves the person owns the inbox, so this is where the password is chosen.
 */
export default function CandidateClaimAccount() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { claimAccount } = useCandidateAuth();
  const token = params.get('token') || '';
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) return setError('Password must be at least 8 characters');
    if (password !== confirm) return setError('Passwords do not match');
    setLoading(true);
    try {
      await claimAccount({ token, password, ...(name.trim() ? { name: name.trim() } : {}) });
      navigate('/candidate/applications');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'This link is invalid or has expired.');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthLayout role="candidate">
        <div className="text-center space-y-3">
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-primary">Invalid link</h1>
          <p className="text-sm text-[var(--text-secondary)]">This link is missing its token.</p>
          <Link to="/candidate/register" className="text-[var(--action-primary)] hover:underline text-sm">Start again</Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout role="candidate">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-primary">Finish setting up your account</h1>
          <p className="mt-1.5 text-sm text-secondary">
            Choose a password. Your earlier applications, CV and interview history will be attached to this account.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="glass-card space-y-3">
          {error && (
            <div className="rounded-md bg-error-bg px-3 py-2.5 text-[13px] text-error-text" role="alert">
              {error}{' '}
              <Link to="/candidate/register" className="underline">Start again</Link>
            </div>
          )}
          <Input label="Full name (optional)" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" />
          <Input label="Confirm password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} autoComplete="new-password" />
          <Button type="submit" size="lg" loading={loading} className="w-full">Create my account</Button>
        </form>
      </div>
    </AuthLayout>
  );
}
