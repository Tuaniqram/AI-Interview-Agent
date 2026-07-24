import { useNavigate, Link } from 'react-router-dom';
import { LoginForm } from '../../components/auth/LoginForm';
import { useAuth } from '../../contexts/AuthContext';
import { useEffect } from 'react';

export default function Login() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate(user?.is_admin ? '/admin' : '/dashboard', { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-page)] px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Welcome Back</h1>
          <p className="mt-2 text-[var(--text-secondary)]">
            Sign in to your account to continue
          </p>
        </div>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 shadow-sm border border-[var(--border-color)]">
          <LoginForm />
        </div>
        <p className="text-center text-sm text-[var(--text-secondary)]">
          Don't have an account?{' '}
          <Link to="/register" className="text-[var(--action-primary)] hover:underline">
            Create one
          </Link>
        </p>
        <p className="mt-2 text-center text-sm text-[var(--text-secondary)]">
          Are you a candidate?{' '}
          <Link to="/candidate/login" className="text-[var(--action-primary)] hover:underline">
            Sign in here
          </Link>
        </p>
      </div>
    </div>
  );
}
