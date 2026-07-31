import { useEffect, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { apiClient } from '../../services/apiClient';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { useToast } from '../../components/shared/Toast';
import { Cpu, Activity, CheckCircle, XCircle } from 'lucide-react';

export default function LLMDashboard() {
  const { activeOrg } = useOrg();
  const toast = useToast();
  const [status, setStatus] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    Promise.all([
      apiClient.get(`/api/v1/orgs/${activeOrg.id}/llm-status`),
      apiClient.get(`/api/v1/orgs/${activeOrg.id}/llm-usage`),
    ]).then(([s, u]) => {
      setStatus(s);
      setUsage(u);
    }).catch(() => toast.error('Failed to load LLM data'))
    .finally(() => setLoading(false));
  }, [activeOrg?.id]);

  if (loading) return <ContentSkeleton />;

  return (
    <div className="space-y-6">
      <PageHeader title="LLM Dashboard" description="AI model configuration and usage" />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card padding="lg">
          <div className="flex items-center gap-3">
            <Cpu className="w-5 h-5 text-action-primary" />
            <div>
              <p className="text-xs text-muted">Model Chain</p>
              <p className="text-sm font-semibold text-primary">{status?.model_chain || '—'}</p>
            </div>
          </div>
        </Card>
        <Card padding="lg">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-action-primary" />
            <div>
              <p className="text-xs text-muted">Total Interviews</p>
              <p className="text-sm font-semibold text-primary">{usage?.total_interviews || 0}</p>
            </div>
          </div>
        </Card>
        <Card padding="lg">
          <div className="flex items-center gap-3">
            <Cpu className="w-5 h-5 text-action-primary" />
            <div>
              <p className="text-xs text-muted">Est. LLM Calls</p>
              <p className="text-sm font-semibold text-primary">{usage?.estimated_llm_calls?.toLocaleString() || 0}</p>
            </div>
          </div>
        </Card>
      </div>

      <Card padding="lg">
        <h3 className="text-sm font-semibold text-primary mb-3">Provider Status</h3>
        <div className="space-y-2">
          {status?.providers?.map((p: any) => (
            <div key={p.name} className="flex items-center gap-3 p-2 rounded-lg bg-page border border-border">
              {p.configured ? <CheckCircle className="w-4 h-4 text-success" /> : <XCircle className="w-4 h-4 text-muted" />}
              <span className="text-sm text-primary">{p.name}</span>
              <span className="text-xs text-muted ml-auto">{p.configured ? 'Configured' : 'Not configured'}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
