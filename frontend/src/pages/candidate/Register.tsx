import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useCandidateAuth } from '../../contexts/CandidateAuthContext';
import { useGoogleLogin } from '@react-oauth/google';

export default function CandidateRegister() {
  const navigate = useNavigate();
  const { register, googleLogin } = useCandidateAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register({ name, email, password });
      navigate('/candidate/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const googleLoginHandler = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        await googleLogin(tokenResponse.access_token);
        navigate('/candidate/dashboard');
      } catch (err) {
        setError('Google sign up failed');
      }
    },
    onError: () => setError('Google sign up failed'),
  });

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Create Candidate Account</h1>
          <p className="mt-2 text-[var(--text-secondary)]">Track your interviews and practice with AI</p>
        </div>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)] space-y-4">
          <button
            onClick={() => googleLoginHandler()}
            className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-lg border border-[var(--border-color)] text-[var(--text-primary)] hover:bg-[var(--bg-page)] transition-colors"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Sign up with Google
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-[var(--border-color)]" /></div>
            <div className="relative flex justify-center text-xs"><span className="bg-[var(--bg-section)] px-2 text-[var(--text-secondary)]">or</span></div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <div className="text-sm text-red-500">{error}</div>}
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Full Name</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]" required minLength={6} />
            </div>
            <button type="submit" disabled={loading} className="w-full px-4 py-2 rounded-lg bg-[var(--action-primary)] text-white font-medium hover:opacity-90 disabled:opacity-50">
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>
        </div>
        <p className="text-center text-sm text-[var(--text-secondary)]">
          Already have an account? <Link to="/candidate/login" className="text-[var(--action-primary)] hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
