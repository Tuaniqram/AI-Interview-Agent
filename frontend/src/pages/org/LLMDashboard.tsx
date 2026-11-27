import { useEffect, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { PageHeader } from '../../components/shared/PageHeader';
import { Card } from '../../components/shared/Card';
import { StatStrip } from '../../components/shared/StatStrip';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { useToast } from '../../components/shared/Toast';

export default function LLMDashboard() {
  const toast = useToast();
  const [status, setStatus] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      apiClient.get('/api/v1/admin/llm-status'),
      apiClient.get('/api/v1/admin/llm-usage'),
    ]).then(([s, u]) => {
      setStatus(s);
      setUsage(u);
    }).catch(() => toast.error('Could not load the model status. Reload the page to try again.'))
    .finally(() => setLoading(false));
  }, []);

  if (loading) return <ContentSkeleton />;

  const providers: { name: string; configured: boolean }[] = status?.providers ?? [];

  return (
    <div className="max-w-4xl space-y-8">
      <PageHeader title="Language models" description="Which models the interviews use, and roughly how many calls they have made." />

      <StatStrip stats={[
        { label: 'Interviews', value: (usage?.total_interviews ?? 0).toLocaleString() },
        { label: 'Estimated model calls', value: (usage?.estimated_llm_calls ?? 0).toLocaleString() },
        { label: 'Providers configured', value: `${providers.filter(p => p.configured).length} of ${providers.length}` },
      ]} />

      <section aria-labelledby="chain-heading">
        <h2 id="chain-heading" className="text-sm font-semibold text-primary">Model chain</h2>
        <p className="text-[13px] text-tertiary mt-0.5 mb-3">Each call tries these in order and falls back to the next when one fails.</p>
        <Card padding="none">
          <ol className="divide-y divide-[var(--divider)]">
            {providers.map((p, i) => (
              <li key={p.name} className="flex items-center gap-3 px-4 py-3">
                <span className="w-6 h-6 rounded-md bg-hover text-secondary text-xs font-semibold flex items-center justify-center shrink-0 tabular">{i + 1}</span>
                <span className="flex-1 min-w-0 text-sm text-primary truncate">{p.name}</span>
                <span className={`inline-flex items-center gap-1.5 text-[13px] ${p.configured ? 'text-success-text' : 'text-tertiary'}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${p.configured ? 'bg-success' : 'bg-tertiary'}`} aria-hidden />
                  {p.configured ? 'Configured' : 'Not configured'}
                </span>
              </li>
            ))}
          </ol>
        </Card>
        {status?.model_chain && <p className="mt-2 text-xs text-tertiary break-all">Raw setting: {status.model_chain}</p>}
      </section>
    </div>
  );
}
