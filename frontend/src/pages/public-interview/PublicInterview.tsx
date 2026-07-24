import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

export default function PublicInterview() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/public/interviews/${token}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_name: name, candidate_email: email }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to start interview');
      }
      const data = await res.json();
      navigate(`/interview/${data.session_id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-page)] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            You've been invited to an interview
          </h1>
          <p className="text-[var(--text-secondary)] mt-2">
            Enter your details to get started
          </p>
        </div>
        <div className="bg-[var(--bg-section)] rounded-xl p-6 border border-[var(--border-color)]">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-600">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">
                Your Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-page)] text-[var(--text-primary)]"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 rounded-lg bg-[var(--action-primary)] text-white font-medium hover:opacity-90 disabled:opacity-50"
            >
              {loading ? 'Starting...' : 'Start Interview'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
