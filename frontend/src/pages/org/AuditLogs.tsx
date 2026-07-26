import { useEffect, useState } from 'react';
import { useOrg } from '../../contexts/OrgContext';
import { apiClient } from '../../services/apiClient';
import { PageHeader } from '../../components/shared/PageHeader';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { EmptyState } from '../../components/shared/EmptyState';
import { useToast } from '../../components/shared/Toast';

interface AuditEntry {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: string | null;
  ip_address: string | null;
  created_at: string | null;
}

export default function AuditLogs() {
  const { activeOrg } = useOrg();
  const toast = useToast();
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');

  useEffect(() => {
    if (!activeOrg?.id) return;
    setLoading(true);
    apiClient.get<AuditEntry[]>(`/api/v1/orgs/${activeOrg.id}/audit-logs`)
      .then(setLogs)
      .catch(() => toast.error('Failed to load audit logs'))
      .finally(() => setLoading(false));
  }, [activeOrg?.id]);

  if (loading) return <LoadingSpinner />;

  const actions = [...new Set(logs.map(l => l.action))];
  const filtered = actionFilter ? logs.filter(l => l.action === actionFilter) : logs;

  return (
    <div className="space-y-6">
      <PageHeader title="Audit Logs" description="Track all actions taken in your organization" />

      <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}
        className="px-3 py-2 text-sm bg-input text-primary rounded-lg border border-border">
        <option value="">All Actions</option>
        {actions.map(a => <option key={a} value={a}>{a}</option>)}
      </select>

      {filtered.length === 0 ? (
        <EmptyState title="No audit logs" description="Actions will be recorded here" />
      ) : (
        <div className="space-y-1">
          {filtered.map(log => (
            <div key={log.id} className="flex items-start gap-3 p-3 rounded-lg bg-section border border-border text-xs">
              <span className="px-2 py-0.5 rounded bg-action-primary/10 text-action-primary font-medium shrink-0">{log.action}</span>
              <div className="flex-1 min-w-0">
                <p className="text-primary">
                  {log.resource_type && <span className="text-muted">{log.resource_type} </span>}
                  {log.resource_id && <span className="font-mono text-[10px] text-muted">#{log.resource_id.slice(0, 8)}</span>}
                </p>
                {log.details && <p className="text-muted mt-0.5">{log.details}</p>}
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
