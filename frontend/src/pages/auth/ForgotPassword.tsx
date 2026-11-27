import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthLayout } from '../../components/auth/AuthLayout';
import { Input } from '../../components/shared/Input';
import { Button } from '../../components/shared/Button';
import { authService } from '../../services/authService';

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
      await authService.forgotPassword(email);
      setSent(true);
    } catch {
      setError('Failed to send reset email. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout role="org">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-primary">Forgot your password?</h1>
          <p className="mt-1.5 text-sm text-secondary">Enter your email and we'll send you a reset link</p>
        </div>
        <div className="glass-card">
          {sent ? (
            <p className="text-sm text-[var(--text-secondary)] text-center">If that email exists, a reset link has been sent.</p>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-3">
              {error && (
                <div className="rounded-md bg-error-bg px-3 py-2.5 text-[13px] text-error-text">{error}</div>
              )}
              <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              <Button type="submit" size="lg" loading={loading} className="w-full">Send reset link</Button>
            </form>
          )}
        </div>
        <p className="text-sm text-secondary">
          <Link to="/login" className="text-[var(--action-primary)] hover:underline">Back to sign in</Link>
        </p>
      </div>
    </AuthLayout>
  );
}
