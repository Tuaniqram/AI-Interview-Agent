import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthLayout } from '../../components/auth/AuthLayout';
import { Input } from '../../components/shared/Input';
import { Button } from '../../components/shared/Button';
import { candidateService } from '../../services/candidateService';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await candidateService.forgotPassword(email);
      setSent(true);
    } catch {
      setError('Failed to send reset email. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout role="candidate">
      <div className="space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Forgot Password</h1>
          <p className="mt-2 text-[var(--text-secondary)]">Enter your email and we'll send you a reset link</p>
        </div>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)]">
          {sent ? (
            <p className="text-sm text-[var(--text-secondary)] text-center">If that email exists, a reset link has been sent.</p>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600 dark:text-red-400">{error}</div>
              )}
              <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <Button type="submit" loading={loading} className="w-full">Send Reset Link</Button>
            </form>
          )}
        </div>
        <p className="text-center text-sm text-[var(--text-secondary)]">
          <Link to="/candidate/login" className="text-[var(--action-primary)] hover:underline">Back to sign in</Link>
        </p>
      </div>
    </AuthLayout>
  );
}
