/**
 * Progress Bar Component
 * Displays progress for questions, phases, or general workflows
 */

interface ProgressBarProps {
  current: number;
  total: number;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function ProgressBar({ current, total, label, size = 'md' }: ProgressBarProps) {
  const percentage = Math.min((current / total) * 100, 100);
  
  const sizeClass = {
    sm: 'h-2',
    md: 'h-4',
    lg: 'h-6',
  }[size];

  const labelClass = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }[size];

  return (
    <div className="w-full">
      <div className={`w-full ${sizeClass} bg-gray-200 rounded-full overflow-hidden`}>
        <div
          className={`h-full bg-gradient-to-r from-purple-600 to-indigo-600 transition-all duration-500 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {label && (
        <div className={`mt-2 flex justify-between ${labelClass}`} style={{ width: 'fit-content' }}>
          <span className="text-gray-600">{label}</span>
          <span className="font-semibold text-gray-800">
            {current} / {total}
          </span>
        </div>
      )}
    </div>
  );
}