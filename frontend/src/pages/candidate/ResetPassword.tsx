import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AuthLayout } from '../../components/auth/AuthLayout';
import { Input } from '../../components/shared/Input';
import { Button } from '../../components/shared/Button';
import { candidateService } from '../../services/candidateService';

/** Target of the password-reset email link: /candidate/reset-password?token=... */
export default function CandidateResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) return setError('Password must be at least 8 characters');
    if (password !== confirm) return setError('Passwords do not match');
    setLoading(true);
    try {
      await candidateService.resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate('/candidate/login'), 2500);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'This reset link is invalid or has expired.');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthLayout role="candidate">
        <div className="text-center space-y-3">
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Invalid link</h1>
          <p className="text-sm text-[var(--text-secondary)]">This reset link is missing its token.</p>
          <Link to="/candidate/forgot-password" className="text-[var(--action-primary)] hover:underline text-sm">Request a new link</Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout role="candidate">
      <div className="space-y-4">
        <div className="text-center">
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Choose a new password</h1>
        </div>
        {done ? (
          <div className="glass-card text-sm text-[var(--text-secondary)]" role="status">
            Password updated. Redirecting you to sign in…
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="glass-card space-y-3">
            {error && (
              <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600 dark:text-red-400" role="alert">
                {error}{' '}
                <Link to="/candidate/forgot-password" className="underline">Request a new link</Link>
              </div>
            )}
            <Input label="New password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" />
            <Input label="Confirm password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} autoComplete="new-password" />
            <Button type="submit" loading={loading} className="w-full">Update password</Button>
          </form>
        )}
      </div>
    </AuthLayout>
  );
}
