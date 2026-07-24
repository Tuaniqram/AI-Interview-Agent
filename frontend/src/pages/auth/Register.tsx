import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Input } from '../../components/shared/Input';
import { Button } from '../../components/shared/Button';

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [orgName, setOrgName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register({ name, email, password, org_name: orgName || 'My Organization' });
      navigate('/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Create Account</h1>
          <p className="mt-2 text-[var(--text-secondary)]">
            Get started with AI Interview Agent
          </p>
        </div>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600 dark:text-red-400">
                {error}
              </div>
            )}
            <Input label="Full Name" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <Input label="Organization Name" value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="My Organization" />
            <Button type="submit" loading={loading} className="w-full">
              Create Account
            </Button>
          </form>
        </div>
        <p className="text-center text-sm text-[var(--text-secondary)]">
          Already have an account?{' '}
          <Link to="/login" className="text-[var(--action-primary)] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
