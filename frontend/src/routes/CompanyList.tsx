import { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { apiClient } from '../services/apiClient';
import { PageHeader } from '../components/shared/PageHeader';
import { SearchInput } from '../components/shared/SearchInput';
import { CompanyCard } from '../components/company/CompanyCard';
import { CompanyForm } from '../components/company/CompanyForm';
import { EmptyState } from '../components/shared/EmptyState';
import { CardSkeleton } from '../components/shared/Skeleton';
import { Building2 } from 'lucide-react';

interface Company {
  id: number;
  name: string;
  website?: string | null;
  description?: string | null;
  created_at: string;
}

interface CompanyWithCounts extends Company {
  docCount: number;
  sessionCount: number;
}

export function CompanyList() {
  const [companies, setCompanies] = useState<CompanyWithCounts[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiClient.get<Company[]>('/companies/');

      const enriched = await Promise.all(
        data.map(async (c) => {
          const [docs, sessions] = await Promise.allSettled([
            apiClient.get<any[]>(`/companies/${c.id}/knowledge`),
            apiClient.get<any[]>(`/companies/${c.id}/sessions`),
          ]);
          return {
            ...c,
            docCount: docs.status === 'fulfilled' ? docs.value.length : 0,
            sessionCount: sessions.status === 'fulfilled' ? sessions.value.length : 0,
          };
        })
      );

      setCompanies(enriched);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async (data: { name: string; website: string; description: string }) => {
    try {
      await apiClient.post('/companies/', data);
      setShowForm(false);
      load();
    } catch {
      // silent
    }
  };

  const filtered = companies.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    (c.website || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <PageHeader
        title="Companies"
        description="Manage companies and their interview configurations"
        actions={
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Company
          </button>
        }
      />

      <div className="mb-6">
        <SearchInput value={search} onChange={setSearch} placeholder="Search companies..." className="max-w-xs" />
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1,2,3,4].map(i => <CardSkeleton key={i} />)}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Building2 className="w-8 h-8" />}
          title={search ? 'No companies match your search' : 'No companies yet'}
          description="Add your first company to start conducting AI interviews."
          action={
            <button onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover">
              <Plus className="w-4 h-4" /> Add Company
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map(c => (
            <CompanyCard
              key={c.id}
              company={c}
              docCount={c.docCount}
              sessionCount={c.sessionCount}
            />
          ))}
        </div>
      )}

      <CompanyForm open={showForm} onSave={handleSave} onCancel={() => setShowForm(false)} />
    </div>
  );
}
