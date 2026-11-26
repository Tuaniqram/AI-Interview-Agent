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
      <PageHeader title="Audit logs" description="Who did what, across every organization. Newest first." />

      <div className="flex items-center gap-3">
        <Select
          className="w-64"
          value={actionFilter}
          onChange={setActionFilter}
          placeholder="All actions"
          options={[{ value: '', label: 'All actions' }, ...actions.map(a => ({ value: a, label: humanizeAction(a) }))]}
        />
        <span className="text-[13px] text-tertiary tabular">{filtered.length} {filtered.length === 1 ? 'entry' : 'entries'}</span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="Nothing recorded yet" description="Actions such as creating a listing or inviting a member are recorded here." />
      ) : (
        <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)]">
          {filtered.map(log => (
            <li key={log.id} className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-4 px-4 py-3 text-[13px]">
              <span className="sm:w-48 shrink-0 font-medium text-primary">{humanizeAction(log.action)}</span>
              <div className="flex-1 min-w-0">
                <p className="text-secondary">
                  {log.org_name && <span className="text-primary">{log.org_name} </span>}
                  {log.resource_type && <span>{humanizeName(log.resource_type)} </span>}
                  {log.resource_id && <span className="text-tertiary tabular">#{log.resource_id.slice(0, 8)}</span>}
                </p>
                {log.details && (typeof log.details === 'string' || Object.keys(log.details).length > 0) && (
                  <p className="text-xs text-tertiary mt-0.5 break-all">
                    {summarizeDetails(log.details)}
                  </p>
                )}
              </div>
              <div className="sm:text-right shrink-0 text-xs text-tertiary tabular">
                <p>{log.created_at ? new Date(log.created_at).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}</p>
                {log.ip_address && <p>{log.ip_address}</p>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
