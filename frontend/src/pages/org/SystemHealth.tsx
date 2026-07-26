import { useEffect, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { CheckCircle, XCircle, Activity } from 'lucide-react';

interface HealthStatus {
  status: string;
  app: string;
  version: string;
}

export default function SystemHealth() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [dbStatus, setDbStatus] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiClient.get<HealthStatus>('/api/v1/health'),
      apiClient.get('/api/v1/health').then(() => true).catch(() => false),
    ]).then(([h, db]) => {
      setHealth(h);
      setDbStatus(db);
    }).catch(() => {
      setDbStatus(false);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  const checks = [
    { label: 'API Server', ok: health?.status === 'ok', detail: `${health?.app} v${health?.version}` },
    { label: 'Database', ok: dbStatus === true, detail: dbStatus ? 'Connected' : 'Disconnected' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="System Health" description="Monitor system components and services" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {checks.map(c => (
          <Card key={c.label} padding="lg">
            <div className="flex items-center gap-3">
              {c.ok ? <CheckCircle className="w-5 h-5 text-success" /> : <XCircle className="w-5 h-5 text-error" />}
              <div>
                <p className="text-sm font-semibold text-primary">{c.label}</p>
                <p className="text-xs text-muted">{c.detail}</p>
              </div>
            </div>
          </Card>
        ))}
        <Card padding="lg">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-action-primary" />
            <div>
              <p className="text-sm font-semibold text-primary">Environment</p>
              <p className="text-xs text-muted">{import.meta.env.MODE}</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
