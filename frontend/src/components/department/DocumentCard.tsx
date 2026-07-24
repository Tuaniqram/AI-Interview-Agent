import { FileText, Trash2 } from 'lucide-react';
import { Card } from '../shared/Card';

interface DocumentCardProps {
  document: {
    id: string;
    filename: string;
    document_type: string;
    created_at: string;
  };
  onDelete?: (id: string) => void;
}

export function DocumentCard({ document, onDelete }: DocumentCardProps) {
  return (
    <Card>
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-hover flex items-center justify-center shrink-0">
          <FileText className="w-4 h-4 text-secondary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-primary truncate">{document.filename}</p>
          <p className="text-xs text-muted">
            {document.document_type.toUpperCase()} · {new Date(document.created_at).toLocaleDateString()}
          </p>
        </div>
        {onDelete && (
          <button
            onClick={() => onDelete(document.id)}
            className="p-1.5 rounded-lg text-muted hover:text-error hover:bg-error-bg transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>
    </Card>
  );
}
