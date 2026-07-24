import { useState } from 'react';
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
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600 dark:text-red-400">
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
      <Button type="submit" loading={loading} className="w-full">
        Sign In
      </Button>
    </form>
  );
}
