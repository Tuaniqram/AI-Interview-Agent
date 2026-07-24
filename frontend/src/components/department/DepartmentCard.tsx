import { useNavigate } from 'react-router-dom';
import { Building2, FileText, ListChecks } from 'lucide-react';
import { Card } from '../shared/Card';

interface DepartmentCardProps {
  department: {
    id: number;
    name: string;
    website?: string | null;
    description?: string | null;
    created_at: string;
  };
  docCount?: number;
  sessionCount?: number;
  avgScore?: number | null;
}

export function DepartmentCard({ department, docCount = 0, sessionCount = 0, avgScore }: DepartmentCardProps) {
  const navigate = useNavigate();

  return (
    <Card hover className="cursor-pointer" onClick={() => navigate(`/departments/${department.id}`)}>
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-lg bg-action-primary/15 flex items-center justify-center shrink-0">
          <Building2 className="w-5 h-5 text-action-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-primary truncate">{department.name}</h3>
          {department.website && (
            <p className="text-xs text-muted truncate mt-0.5">{department.website}</p>
          )}
          {department.description && (
            <p className="text-xs text-secondary mt-1 line-clamp-2">{department.description}</p>
          )}
          <div className="flex items-center gap-4 mt-3 text-xs text-muted">
            <span className="flex items-center gap-1">
              <FileText className="w-3.5 h-3.5" /> {docCount} docs
            </span>
            <span className="flex items-center gap-1">
              <ListChecks className="w-3.5 h-3.5" /> {sessionCount} sessions
            </span>
            {avgScore !== null && avgScore !== undefined && (
              <span className={`font-medium ${avgScore >= 7 ? 'text-success' : avgScore >= 5 ? 'text-warning' : 'text-error'}`}>
                {avgScore.toFixed(1)} avg
              </span>
            )}
          </div>
          <p className="text-xs text-muted mt-1">
            Created {new Date(department.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>
    </Card>
  );
}
