import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Button } from './Button';

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

/**
 * A yes/no question. For a destructive action, focus starts on Cancel, so Enter alone never deletes.
 */
export function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', variant = 'default', onConfirm, onCancel }: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const textId = useId();

  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    (variant === 'danger' ? cancelRef : confirmRef).current?.focus();

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); onCancel(); }
      if (e.key === 'Tab') {
        const items = dialogRef.current?.querySelectorAll<HTMLElement>('button');
        if (!items || items.length === 0) return;
        const first = items[0], last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    // Capture, so Esc here does not also close a sheet underneath.
    document.addEventListener('keydown', handleKey, true);
    return () => {
      document.removeEventListener('keydown', handleKey, true);
      opener?.focus?.();
    };
  }, [open, onCancel, variant]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-overlay animate-fade-in" onClick={onCancel} aria-hidden />
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={textId}
        className="relative bg-section border border-border rounded-xl shadow-xl w-full max-w-sm p-5 animate-fade-in"
      >
        <h2 id={titleId} className="text-base font-semibold text-primary">{title}</h2>
        <p id={textId} className="text-[13px] text-secondary mt-1.5">{message}</p>
        <div className="flex justify-end gap-2 mt-5">
          <Button ref={cancelRef} variant="secondary" onClick={onCancel}>{cancelLabel}</Button>
          <Button ref={confirmRef} variant={variant === 'danger' ? 'danger' : 'primary'} onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
