interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

type Tone = 'neutral' | 'success' | 'info' | 'warning' | 'error' | 'accent';

const tones: Record<Tone, { dot: string; bg: string; text: string }> = {
  neutral: { dot: 'bg-tertiary', bg: 'bg-hover', text: 'text-secondary' },
  success: { dot: 'bg-success', bg: 'bg-success-bg', text: 'text-success-text' },
  info: { dot: 'bg-info', bg: 'bg-info-bg', text: 'text-info-text' },
  warning: { dot: 'bg-warning', bg: 'bg-warning-bg', text: 'text-warning-text' },
  error: { dot: 'bg-error', bg: 'bg-error-bg', text: 'text-error-text' },
  accent: { dot: 'bg-action-primary', bg: 'bg-action-primary-soft', text: 'text-action-primary' },
};

/** `live` statuses are happening right now; only those pulse. */
const variants: Record<string, { tone: Tone; label: string; live?: boolean }> = {
  active: { tone: 'success', label: 'Active' },
  completed: { tone: 'info', label: 'Completed' },
  in_progress: { tone: 'warning', label: 'In progress', live: true },
  initiated: { tone: 'neutral', label: 'Initiated' },
  error: { tone: 'error', label: 'Error' },
  uploading: { tone: 'accent', label: 'Uploading', live: true },
  processed: { tone: 'success', label: 'Processed' },
  initiating: { tone: 'neutral', label: 'Initiating', live: true },
  intro: { tone: 'info', label: 'Intro' },
  answering: { tone: 'warning', label: 'Answering', live: true },
  evaluating: { tone: 'accent', label: 'Evaluating', live: true },
  evaluation_display: { tone: 'success', label: 'Feedback' },
  preparing_next: { tone: 'warning', label: 'Preparing', live: true },
  question_ready: { tone: 'success', label: 'Ready' },
  avatar_speaking: { tone: 'info', label: 'Speaking', live: true },
  avatar_listening: { tone: 'warning', label: 'Listening', live: true },
};

function humanize(status: string): string {
  const s = status.replace(/_/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const v = variants[status] ?? { tone: 'neutral' as Tone, label: humanize(status) };
  const t = tones[v.tone];
  const textSize = size === 'sm' ? 'text-xs h-5' : 'text-[13px] h-6';

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 rounded-md font-medium whitespace-nowrap ${t.bg} ${t.text} ${textSize}`}>
      <span className="relative w-1.5 h-1.5 shrink-0">
        {v.live && <span className={`absolute inset-0 rounded-full ${t.dot} pulse-ring`} />}
        <span className={`absolute inset-0 rounded-full ${t.dot}`} />
      </span>
      {v.label}
    </span>
  );
}
