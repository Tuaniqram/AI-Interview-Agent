interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

const variants: Record<string, { dot: string; bg: string; text: string; label: string }> = {
  active:           { dot: 'bg-success', bg: 'bg-success-bg', text: 'text-success-text', label: 'Active' },
  completed:        { dot: 'bg-info',    bg: 'bg-info-bg',    text: 'text-info-text',    label: 'Completed' },
  in_progress:      { dot: 'bg-warning', bg: 'bg-warning-bg',  text: 'text-warning-text',  label: 'In Progress' },
  initiated:        { dot: 'bg-muted',   bg: 'bg-hover',      text: 'text-muted',        label: 'Initiated' },
  error:            { dot: 'bg-error',   bg: 'bg-error-bg',   text: 'text-error-text',   label: 'Error' },
  uploading:        { dot: 'bg-action-primary', bg: 'bg-action-primary/15', text: 'text-action-primary', label: 'Uploading' },
  processed:        { dot: 'bg-success', bg: 'bg-success-bg', text: 'text-success-text', label: 'Processed' },
  initiating:       { dot: 'bg-muted',   bg: 'bg-hover',      text: 'text-muted',        label: 'Initiating' },
  intro:            { dot: 'bg-info',    bg: 'bg-info-bg',    text: 'text-info-text',    label: 'Intro' },
  answering:        { dot: 'bg-warning', bg: 'bg-warning-bg',  text: 'text-warning-text',  label: 'Answering' },
  evaluating:       { dot: 'bg-primary', bg: 'bg-action-primary/15', text: 'text-action-primary', label: 'Evaluating' },
  evaluation_display:{ dot: 'bg-success', bg: 'bg-success-bg', text: 'text-success-text', label: 'Feedback' },
  preparing_next:   { dot: 'bg-warning', bg: 'bg-warning-bg',  text: 'text-warning-text',  label: 'Preparing' },
  question_ready:   { dot: 'bg-success', bg: 'bg-success-bg', text: 'text-success-text', label: 'Ready' },
  avatar_speaking:  { dot: 'bg-info',    bg: 'bg-info-bg',    text: 'text-info-text',    label: 'Speaking' },
  avatar_listening: { dot: 'bg-warning', bg: 'bg-warning-bg',  text: 'text-warning-text',  label: 'Listening' },
};

export function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const v = variants[status] || { dot: 'bg-muted', bg: 'bg-section', text: 'text-secondary', label: status };
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-medium ${v.bg} ${v.text} ${textSize}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${v.dot}`} />
      {v.label}
    </span>
  );
}
