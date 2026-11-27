import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, ChevronRight, Cpu, HeartPulse, Mail, ScrollText, Users } from 'lucide-react';
import { adminService } from '../../services/adminService';
import { PageHeader } from '../../components/shared/PageHeader';
import { StatStrip } from '../../components/shared/StatStrip';
import { useToast } from '../../components/shared/Toast';
import type { PlatformStats } from '../../types/admin';

const SECTIONS = [
  { to: '/admin/organizations', icon: Building2, title: 'Organizations', text: 'Every organization on the platform and its members' },
  { to: '/admin/users', icon: Users, title: 'Users', text: 'Accounts, roles and whether they are active' },
  { to: '/admin/audit-logs', icon: ScrollText, title: 'Audit logs', text: 'Who did what, across all organizations' },
  { to: '/admin/llm', icon: Cpu, title: 'Language models', text: 'The model chain and estimated usage' },
  { to: '/admin/email-templates', icon: Mail, title: 'Emails', text: 'The messages the platform sends' },
  { to: '/admin/health', icon: HeartPulse, title: 'System health', text: 'API and session store status' },
];

export default function AdminDashboard() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    adminService.getStats()
      .then(setStats)
      .catch(() => toast.error('Could not load platform figures. Reload the page to try again.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader title="Platform" description="Everything across all organizations." />

      <StatStrip loading={loading} stats={[
        { label: 'Organizations', value: String(stats?.total_orgs ?? 0), to: '/admin/organizations' },
        { label: 'Users', value: String(stats?.total_users ?? 0), to: '/admin/users' },
        { label: 'Interviews', value: String(stats?.total_interviews ?? 0) },
        { label: 'In progress now', value: String(stats?.active_sessions ?? 0) },
      ]} />

      <section aria-labelledby="sections-heading">
        <h2 id="sections-heading" className="text-sm font-semibold text-primary mb-3">Manage</h2>
        <div className="rounded-xl border border-border bg-border overflow-hidden">
          <ul className="grid sm:grid-cols-2 gap-px">
            {SECTIONS.map(({ to, icon: Icon, title, text }) => (
              <li key={to} className="bg-section">
                <Link to={to} className="group flex items-center gap-3 px-4 py-3.5 hover:bg-subtle transition-colors">
                  <span className="w-8 h-8 rounded-lg border border-border bg-subtle flex items-center justify-center text-secondary shrink-0">
                    <Icon className="w-4 h-4" />
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-[13px] font-medium text-primary">{title}</span>
                    <span className="block text-xs text-tertiary truncate">{text}</span>
                  </span>
                  <ChevronRight className="w-4 h-4 text-tertiary group-hover:text-primary" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
