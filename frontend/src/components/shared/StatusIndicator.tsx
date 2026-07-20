/**
 * Status Indicator Component
 * Displays interview phase/health status
 */

import { CheckCircle2, Loader2 } from 'lucide-react';

interface StatusIndicatorProps {
  status: string;
  showLoader?: boolean;
  message?: string;
}

export function StatusIndicator({ status, showLoader = false, message }: StatusIndicatorProps) {
  if (showLoader) {
    return (
      <div className="flex items-center gap-2 text-action-primary">
        <Loader2 className="animate-spin" />
        <span>{message || 'Loading...'}</span>
      </div>
    );
  }

  const getStatusStyles = () => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'in_progress':
        return {
          icon: CheckCircle2,
          color: 'text-success',
          bgColor: 'bg-success-bg',
          label: 'Active'
        };
      case 'completed':
        return {
          icon: CheckCircle2,
          color: 'text-action-primary',
          bgColor: 'bg-action-primary/15',
          label: 'Completed'
        };
      case 'initiating':
        return {
          icon: Loader2,
          color: 'text-info',
          bgColor: 'bg-info-bg',
          label: 'Initializing'
        };
      default:
        return {
          icon: CheckCircle2,
          color: 'text-muted',
          bgColor: 'bg-hover',
          label: status
        };
    }
  };

  const { icon: Icon, color, bgColor, label } = getStatusStyles();

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${bgColor} text-sm font-medium ${color}`}>
      <Icon size={16} />
      <span>{label}</span>
    </div>
  );
}