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
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Invalid Link</h1>
          <p className="text-[var(--text-secondary)]">This reset link is missing or invalid.</p>
          <Link to="/forgot-password" className="text-[var(--action-primary)] hover:underline">Request a new link</Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout role="org">
      <div className="space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Reset Password</h1>
          <p className="mt-2 text-[var(--text-secondary)]">Choose a new password for your account</p>
        </div>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)]">
          {success ? (
            <div className="text-center space-y-4">
              <p className="text-sm text-green-600 dark:text-green-400">Password reset successfully! Redirecting to sign in...</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600 dark:text-red-400">{error}</div>
              )}
              <Input label="New Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              <Input label="Confirm Password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
              <Button type="submit" loading={loading} className="w-full">Reset Password</Button>
            </form>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
