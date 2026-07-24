import { useEffect, useRef } from 'react';
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
  const dialogRef = useRef<HTMLDivElement>(null);
  const confirmBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    confirmBtnRef.current?.focus();

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
      if (e.key === 'Tab') {
        const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (!focusable || focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-overlay" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div ref={dialogRef} className="bg-elevated rounded-xl shadow-lg max-w-sm w-full mx-4 p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${variant === 'danger' ? 'bg-error-bg' : 'bg-hover'}`}>
              <AlertTriangle className={`w-5 h-5 ${variant === 'danger' ? 'text-error' : 'text-secondary'}`} />
            </div>
            <h3 id="confirm-title" className="font-semibold text-primary">{title}</h3>
          </div>
          <button onClick={onCancel} className="text-muted hover:text-secondary" aria-label="Close"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-sm text-secondary mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel} ref={variant !== 'danger' ? confirmBtnRef : undefined}
            className="px-4 py-2 text-sm font-medium text-action-ghost-text bg-action-ghost-hover rounded-lg hover:bg-action-secondary-hover transition-colors">
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            ref={variant === 'danger' ? confirmBtnRef : undefined}
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