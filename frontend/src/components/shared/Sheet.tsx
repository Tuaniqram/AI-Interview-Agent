import { FormEvent, ReactNode, useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

interface SheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  /** The action row, pinned to the bottom (Cancel / Save). */
  footer?: ReactNode;
  /** When given, the body and footer are one form, so Enter in a field and a submit button both save. */
  onSubmit?: (e: FormEvent) => void;
  width?: 'md' | 'lg';
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * An editor that slides in from the right over the page: the list stays in view behind it, the
 * header and actions stay put while the fields scroll. Esc, the close button and the backdrop close it;
 * focus is kept inside while open and returned to whatever opened it.
 */
export function Sheet({ open, onClose, title, description, children, footer, onSubmit, width = 'md' }: SheetProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    // First field, not the close button: the sheet was opened to fill something in.
    const first = panel?.querySelector<HTMLElement>('input:not([type="hidden"]):not([disabled]), textarea, select');
    (first ?? panel)?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // A dropdown inside the sheet closes itself first.
        if (!e.defaultPrevented) closeRef.current();
        return;
      }
      if (e.key !== 'Tab' || !panel) return;
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(el => el.offsetParent !== null);
      if (items.length === 0) return;
      const a = items[0], z = items[items.length - 1];
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
      else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
      opener?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  const body = (
    <>
      <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
      {footer && <div className="shrink-0 flex items-center justify-end gap-2 px-6 py-3.5 border-t border-border bg-section">{footer}</div>}
    </>
  );

  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-overlay animate-fade-in" onClick={onClose} aria-hidden />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={`relative h-full w-full ${width === 'lg' ? 'sm:max-w-2xl' : 'sm:max-w-xl'} bg-section border-l border-border shadow-xl flex flex-col outline-none animate-sheet-in`}
      >
        <header className="shrink-0 flex items-start gap-4 px-6 pt-5 pb-4 border-b border-border">
          <div className="flex-1 min-w-0">
            <h2 id={titleId} className="text-base font-semibold text-primary">{title}</h2>
            {description && <div className="text-[13px] text-secondary mt-1">{description}</div>}
          </div>
          <button type="button" onClick={onClose} className="p-1.5 -mr-1.5 rounded-md text-tertiary hover:text-primary hover:bg-hover" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </header>
        {onSubmit ? <form onSubmit={onSubmit} className="flex-1 min-h-0 flex flex-col">{body}</form> : body}
      </div>
    </div>,
    document.body,
  );
}

/** A titled group of fields inside a sheet. */
export function SheetSection({ title, text, children, action }: { title: string; text?: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="py-5 first:pt-0 border-b border-border last:border-0 last:pb-0">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <h3 className="text-[13px] font-semibold text-primary">{title}</h3>
          {text && <p className="text-xs text-tertiary mt-0.5">{text}</p>}
        </div>
        {action}
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}
