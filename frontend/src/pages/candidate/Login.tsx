import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';

export default function CandidateLogin() {
  const navigate = useNavigate();
  const { login } = useCandidateAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login({ email, password });
      navigate('/candidate/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Candidate Sign In</h1>
          <p className="mt-2 text-[var(--text-secondary)]">Access your interview history and practice</p>
        </div>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <div className="text-sm text-red-500">{error}</div>}
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" required />
            </div>
            <button type="submit" disabled={loading} className="w-full px-4 py-2 rounded-lg bg-[var(--action-primary)] text-white font-medium hover:opacity-90 disabled:opacity-50">
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
        <p className="text-center text-sm text-[var(--text-secondary)]">
          Don't have an account? <Link to="/candidate/register" className="text-[var(--action-primary)] hover:underline">Create one</Link>
        </p>
        <p className="mt-2 text-center text-sm text-[var(--text-secondary)]">
          Are you from an organization?{' '}
          <Link to="/login" className="text-[var(--action-primary)] hover:underline">
            Sign in here
          </Link>
        </p>
      </div>
    </div>
  );
}
