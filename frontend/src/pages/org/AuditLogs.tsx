import { useEffect, useState } from 'react';
import { apiClient } from '../../services/apiClient';
import { PageHeader } from '../../components/shared/PageHeader';
import { ContentSkeleton } from '../../components/shared/ContentSkeleton';
import { EmptyState } from '../../components/shared/EmptyState';
import { Select } from '../../components/shared/Select';
import { useToast } from '../../components/shared/Toast';
import { humanizeAction, humanizeName, summarizeDetails } from '../../utils/humanize';

interface AuditEntry {
  id: string;
  org_id?: string | null;
  org_name?: string | null;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | string | null;
  ip_address: string | null;
  created_at: string | null;
}

export default function AuditLogs() {
  const toast = useToast();
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');

  useEffect(() => {
    setLoading(true);
    apiClient.get<AuditEntry[]>('/api/v1/admin/audit-logs')
      .then(setLogs)
      .catch(() => toast.error('Failed to load audit logs'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <ContentSkeleton />;

  const actions = [...new Set(logs.map(l => l.action))];
  const filtered = actionFilter ? logs.filter(l => l.action === actionFilter) : logs;

  return (
    <div className="space-y-6">
      <PageHeader title="Audit Logs" description="Track actions across every organization" />

      <Select
        value={actionFilter}
        onChange={setActionFilter}
        placeholder="All Actions"
        options={actions.map(a => ({ value: a, label: humanizeAction(a) }))}
      />

      {filtered.length === 0 ? (
        <EmptyState title="No audit logs" description="Actions will be recorded here" />
      ) : (
        <div className="space-y-1">
          {filtered.map(log => (
            <div key={log.id} className="flex items-start gap-3 p-3 rounded-lg bg-section border border-border text-xs">
              <span className="px-2 py-0.5 rounded bg-action-primary/10 text-action-primary font-medium shrink-0">{humanizeAction(log.action)}</span>
              <div className="flex-1 min-w-0">
                <p className="text-primary">
                  {log.org_name && <span className="text-secondary font-medium">{log.org_name} </span>}
                  {log.resource_type && <span className="text-muted">{humanizeName(log.resource_type)} </span>}
                  {log.resource_id && <span className="font-mono text-[10px] text-muted">#{log.resource_id.slice(0, 8)}</span>}
                </p>
                {log.details && (typeof log.details === 'string' || Object.keys(log.details).length > 0) && (
                  <p className="text-muted mt-0.5 break-all">
                    {summarizeDetails(log.details)}
                  </p>
                )}
              </div>
              <div className="text-right shrink-0">
                <p className="text-muted">{log.created_at ? new Date(log.created_at).toLocaleString() : ''}</p>
                {log.ip_address && <p className="text-muted">{log.ip_address}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
