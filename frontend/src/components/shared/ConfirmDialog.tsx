import { AlertTriangle, X } from 'lucide-react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', variant = 'default', onConfirm, onCancel }: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-overlay">
      <div className="bg-elevated rounded-xl shadow-lg max-w-sm w-full mx-4 p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${variant === 'danger' ? 'bg-error-bg' : 'bg-hover'}`}>
              <AlertTriangle className={`w-5 h-5 ${variant === 'danger' ? 'text-error' : 'text-secondary'}`} />
            </div>
            <h3 className="font-semibold text-primary">{title}</h3>
          </div>
          <button onClick={onCancel} className="text-muted hover:text-secondary"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-sm text-secondary mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel} className="px-4 py-2 text-sm font-medium text-action-ghost-text bg-action-ghost-hover rounded-lg hover:bg-action-secondary-hover transition-colors">
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm font-medium text-inverse rounded-lg transition-colors ${
              variant === 'danger' ? 'bg-action-danger hover:bg-action-danger-hover' : 'bg-action-primary hover:bg-action-primary-hover'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
