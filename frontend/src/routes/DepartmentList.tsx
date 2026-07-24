import { useEffect, useState } from 'react';
import { Plus, Building2 } from 'lucide-react';
import { departmentService, type Department } from '../services/departmentService';
import { PageHeader } from '../components/shared/PageHeader';
import { SearchInput } from '../components/shared/SearchInput';
import { DepartmentCard } from '../components/department/DepartmentCard';
import { DepartmentForm } from '../components/department/DepartmentForm';
import { EmptyState } from '../components/shared/EmptyState';
import { CardSkeleton } from '../components/shared/Skeleton';
import { useToast } from '../components/shared/Toast';

interface DepartmentWithCounts extends Department {
  docCount: number;
  sessionCount: number;
}

export function DepartmentList() {
  const [departments, setDepartments] = useState<DepartmentWithCounts[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const data = await departmentService.listDepartments();

      const enriched = await Promise.all(
        data.map(async (d) => {
          const [docs, sessions] = await Promise.allSettled([
            departmentService.listDocuments(d.id),
            departmentService.listSessions(d.id),
          ]);
          return {
            ...d,
            docCount: docs.status === 'fulfilled' ? docs.value.length : 0,
            sessionCount: sessions.status === 'fulfilled' ? sessions.value.length : 0,
          };
        })
      );

      setDepartments(enriched);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async (data: { name: string; website: string; description: string }) => {
    try {
      await departmentService.createDepartment(data);
      toast.success('Department created');
      setShowForm(false);
      load();
    } catch {
      toast.error('Failed to create department');
    }
  };

  const filtered = departments.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    (d.website || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <PageHeader
        title="Departments"
        description="Manage departments and their interview configurations"
        actions={
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Department
          </button>
        }
      />

      <div className="mb-6">
        <SearchInput value={search} onChange={setSearch} placeholder="Search departments..." className="max-w-xs" />
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1,2,3,4].map(i => <CardSkeleton key={i} />)}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Building2 className="w-8 h-8" />}
          title={search ? 'No departments match your search' : 'No departments yet'}
          description="Add your first department to start conducting AI interviews."
          action={
            <button onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover">
              <Plus className="w-4 h-4" /> Add Department
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map(d => (
            <DepartmentCard
              key={d.id}
              department={d}
              docCount={d.docCount}
              sessionCount={d.sessionCount}
            />
          ))}
        </div>
      )}

      <DepartmentForm open={showForm} onSave={handleSave} onCancel={() => setShowForm(false)} saving={false} />
    </div>
  );
}
