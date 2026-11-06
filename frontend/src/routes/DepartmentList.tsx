import { useEffect, useState } from 'react';
import { Building2 } from 'lucide-react';
import { departmentService, type Department } from '../services/departmentService';
import { PageHeader } from '../components/shared/PageHeader';
import { DepartmentCard } from '../components/department/DepartmentCard';
import { EmptyState } from '../components/shared/EmptyState';
import { CardSkeleton } from '../components/shared/Skeleton';

interface DepartmentWithCounts extends Department {
  docCount: number;
  sessionCount: number;
}

export function DepartmentList() {
  const [departments, setDepartments] = useState<DepartmentWithCounts[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

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
        if (!cancelled) setDepartments(enriched);
      } catch {
        if (!cancelled) setDepartments([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <PageHeader
        title="IT Department"
        description="Organization documents and interview settings"
      />

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => <CardSkeleton key={i} />)}
        </div>
      ) : departments.length === 0 ? (
        <EmptyState
          icon={<Building2 className="w-8 h-8" />}
          title="No IT department yet"
          description="Your IT department is created automatically with your organization."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {departments.map((d) => (
            <DepartmentCard
              key={d.id}
              department={d}
              docCount={d.docCount}
              sessionCount={d.sessionCount}
            />
          ))}
        </div>
      )}
    </div>
  );
}
