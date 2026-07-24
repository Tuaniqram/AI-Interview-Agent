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
      case 'intro':
      case 'question_ready':
        return {
          icon: CheckCircle2,
          color: 'text-success',
          bgColor: 'bg-success-bg',
          label: status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, ' ')
        };
      case 'completed':
        return {
          icon: CheckCircle2,
          color: 'text-action-primary',
          bgColor: 'bg-action-primary/15',
          label: 'Completed'
        };
      case 'initiating':
      case 'preparing_next':
        return {
          icon: Loader2,
          color: 'text-info',
          bgColor: 'bg-info-bg',
          label: status === 'preparing_next' ? 'Preparing Next' : 'Initializing'
        };
      case 'evaluating':
        return {
          icon: Loader2,
          color: 'text-action-primary',
          bgColor: 'bg-action-primary/15',
          label: 'Evaluating'
        };
      case 'evaluation_display':
        return {
          icon: CheckCircle2,
          color: 'text-success',
          bgColor: 'bg-success-bg',
          label: 'Feedback'
        };
      case 'answering':
      case 'avatar_listening':
        return {
          icon: CheckCircle2,
          color: 'text-warning',
          bgColor: 'bg-warning-bg',
          label: status === 'avatar_listening' ? 'Listening' : 'Answering'
        };
      case 'avatar_speaking':
        return {
          icon: Loader2,
          color: 'text-info',
          bgColor: 'bg-info-bg',
          label: 'Speaking'
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