import { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Input } from '../../components/shared/Input';
import { Button } from '../../components/shared/Button';
import { candidateService } from '../../services/candidateService';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
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
      await candidateService.resetPassword(token, password);
      navigate('/candidate/login');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Reset failed. The link may be expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Reset Password</h1>
          <p className="mt-2 text-[var(--text-secondary)]">Enter your new password</p>
        </div>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)]">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600 dark:text-red-400">{error}</div>
            )}
            <Input label="New Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
            <Input label="Confirm Password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
            <Button type="submit" loading={loading} className="w-full">Reset Password</Button>
          </form>
        </div>
        <p className="text-center text-sm text-[var(--text-secondary)]">
          <Link to="/candidate/login" className="text-[var(--action-primary)] hover:underline">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}
