interface PublicLinkCardProps {
  title: string;
  token: string;
  isOpen: boolean;
  submissionCount: number;
  onToggle?: () => void;
  onCopy?: () => void;
}

export function PublicLinkCard({ title, token, isOpen, submissionCount, onToggle, onCopy }: PublicLinkCardProps) {
  const link = `${window.location.origin}/public-interview/${token}`;

  return (
    <div className="p-4 rounded-xl bg-[var(--bg-section)] border border-[var(--border-color)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="font-semibold text-[var(--text-primary)] truncate">{title}</h3>
          <code className="block mt-1 text-xs text-[var(--text-secondary)] truncate bg-[var(--bg-page)] px-2 py-1 rounded">
            {link}
          </code>
          <p className="text-xs text-[var(--text-secondary)] mt-2">
            {submissionCount} submission{submissionCount !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {onCopy && (
            <button
              onClick={onCopy}
              className="px-3 py-1.5 text-xs rounded-lg border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              Copy
            </button>
          )}
          {onToggle && (
            <span
              className={`px-2 py-1 text-xs rounded-full font-medium ${
                isOpen
                  ? 'bg-green-100 dark:bg-green-900/20 text-green-600'
                  : 'bg-red-100 dark:bg-red-900/20 text-red-600'
              }`}
            >
              {isOpen ? 'Open' : 'Closed'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
