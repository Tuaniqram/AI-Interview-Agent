/**
 * Loading Spinner Component
 * Reusable loading indicator
 */

import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function LoadingSpinner({ message = 'Loading...', size = 'md' }: LoadingSpinnerProps) {
  const sizeClass = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }[size];

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <Loader2 className={`${sizeClass} animate-spin text-action-primary`} />
      {message && <p className="text-secondary text-sm">{message}</p>}
    </div>
  );
}
