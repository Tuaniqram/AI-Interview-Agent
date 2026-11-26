import { useEffect, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';

interface HealthStatus {
  status: string;
  app: string;
  version: string;
}

interface RootHealth {
  redis?: string;
  session_store?: string;
}

type Check = { label: string; state: 'ok' | 'down' | 'info'; detail: string };

const DOT: Record<Check['state'], string> = { ok: 'bg-success', down: 'bg-error', info: 'bg-tertiary' };
const WORD: Record<Check['state'], string> = { ok: 'Working', down: 'Not responding', info: '' };

/**
 * What the API itself reports. Only shows checks the backend actually runs: the API answers, and the
 * session store (Redis) is reachable. The database is not probed by any health endpoint, so it is not listed.
 */
export default function SystemHealth() {
  const [api, setApi] = useState<HealthStatus | null>(null);
  const [root, setRoot] = useState<RootHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);

  const load = () => {
    setLoading(true);
    Promise.allSettled([
      apiClient.get<HealthStatus>('/api/v1/health'),
      apiClient.get<RootHealth>('/health'),
    ]).then(([a, r]) => {
      setApi(a.status === 'fulfilled' ? a.value : null);
      setRoot(r.status === 'fulfilled' ? r.value : null);
      setCheckedAt(new Date());
    }).finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading && !checkedAt) return <ContentSkeleton />;

  const checks: Check[] = [
    {
      label: 'API server',
      state: api?.status === 'ok' ? 'ok' : 'down',
      detail: api ? `${api.app} ${api.version}` : 'The health endpoint did not answer.',
    },
    {
      label: 'Session store',
      state: !root ? 'down' : root.redis === 'ok' || root.session_store === 'memory' ? 'ok' : 'down',
      detail: !root
        ? 'The root health endpoint did not answer.'
        : root.session_store === 'redis' ? `Redis: ${root.redis ?? 'unknown'}` : `In memory (${root.session_store ?? 'unknown'})`,
    },
    { label: 'Frontend build', state: 'info', detail: import.meta.env.MODE },
  ];

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="System health"
        description="What the API reports about itself right now."
        actions={
          <button onClick={load} disabled={loading}
            className="h-8 px-3 rounded-md border border-border-strong text-[13px] font-medium text-primary hover:bg-hover disabled:opacity-50">
            {loading ? 'Checking...' : 'Check again'}
          </button>
        }
      />
      <Card padding="none">
        <ul className="divide-y divide-[var(--divider)]">
          {checks.map(c => (
            <li key={c.label} className="flex items-center gap-3 px-4 py-3.5">
              <span className={`w-2 h-2 rounded-full shrink-0 ${DOT[c.state]}`} aria-hidden />
              <span className="flex-1 min-w-0">
                <span className="block text-sm font-medium text-primary">{c.label}</span>
                <span className="block text-xs text-tertiary truncate">{c.detail}</span>
              </span>
              {WORD[c.state] && (
                <span className={`text-[13px] ${c.state === 'ok' ? 'text-success-text' : 'text-error-text'}`}>{WORD[c.state]}</span>
              )}
            </li>
          ))}
        </ul>
      </Card>
      {checkedAt && <p className="mt-3 text-xs text-tertiary">Checked at {checkedAt.toLocaleTimeString()}. The database is not probed by these endpoints.</p>}
    </div>
  );
}
