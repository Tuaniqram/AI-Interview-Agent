import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthLayout } from '../../components/auth/AuthLayout';
import { Input } from '../../components/shared/Input';
import { Button } from '../../components/shared/Button';
import { candidateService } from '../../services/candidateService';

export default function CandidateForgotPassword() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await candidateService.forgotPassword(email.trim());
      setSent(true); // same message whether or not the email exists
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not send the reset link. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout role="candidate">
      <div className="space-y-4">
        <div className="text-center">
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Reset your password</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">We'll email you a link to choose a new one.</p>
        </div>
        {sent ? (
          <div className="glass-card space-y-3 text-sm text-[var(--text-secondary)]" role="status">
            <p>If an account exists for <strong>{email}</strong>, a reset link is on its way. It expires in 1 hour.</p>
            <p>
              Applied as a guest before and never created an account?{' '}
              <Link to="/candidate/register" className="text-[var(--action-primary)] hover:underline">Create one</Link>{' '}
              with the same email.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="glass-card space-y-3">
            {error && (
              <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600 dark:text-red-400" role="alert">{error}</div>
            )}
            <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
            <Button type="submit" loading={loading} className="w-full">Send reset link</Button>
          </form>
        )}
        <p className="text-center text-sm text-[var(--text-secondary)]">
          <Link to="/candidate/login" className="text-[var(--action-primary)] hover:underline">Back to sign in</Link>
        </p>
      </div>
    </AuthLayout>
  );
}
