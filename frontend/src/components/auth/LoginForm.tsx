import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Input } from '../shared/Input';
import { Button } from '../shared/Button';

interface LoginFormProps {
  redirectOnSuccess?: () => void;
}

export function LoginForm({ redirectOnSuccess }: LoginFormProps) {
  const { login } = useAuth();
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
      redirectOnSuccess?.();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && (
        <div className="rounded-md bg-error-bg px-3 py-2.5 text-[13px] text-error-text">
          {error}
        </div>
      )}
      <Input
        label="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        required
      />
      <Input
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Enter your password"
        required
      />
      <div className="text-right">
        <Link to="/forgot-password" className="text-[13px] hover:underline">Forgot password?</Link>
      </div>
      <Button type="submit" size="lg" loading={loading} className="w-full">
        Sign in
      </Button>
    </form>
  );
}
