import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { AuthLayout } from '../../components/auth/AuthLayout';
import { Input } from '../../components/shared/Input';
import { Button } from '../../components/shared/Button';
import { authService } from '../../services/authService';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    setLoading(true);
    try {
      await authService.resetPassword(token, password);
      setSuccess(true);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid or expired reset link');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthLayout role="org">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-primary">Invalid link</h1>
          <p className="text-[var(--text-secondary)]">This reset link is missing or invalid.</p>
          <Link to="/forgot-password" className="text-[var(--action-primary)] hover:underline">Request a new link</Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout role="org">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.02em] text-primary">Reset your password</h1>
          <p className="mt-1.5 text-sm text-secondary">Choose a new password for your account</p>
        </div>
        <div className="glass-card">
          {success ? (
            <div className="text-center space-y-4">
              <p className="text-sm text-green-600 dark:text-green-400">Password reset successfully! Redirecting to sign in...</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-3">
              {error && (
                <div className="rounded-md bg-error-bg px-3 py-2.5 text-[13px] text-error-text">{error}</div>
              )}
              <Input label="New password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              <Input label="Confirm password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
              <Button type="submit" size="lg" loading={loading} className="w-full">Reset your password</Button>
            </form>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
