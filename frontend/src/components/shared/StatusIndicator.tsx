/**
 * Status Indicator Component
 * Displays interview phase/health status
 */

import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { LoadingSpinner } from './LoadingSpinner';

interface StatusIndicatorProps {
  status: string;
  showLoader?: boolean;
  message?: string;
}

export function StatusIndicator({ status, showLoader = false, message }: StatusIndicatorProps) {
  if (showLoader) {
    return (
      <div className="flex items-center gap-2 text-purple-600">
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
          color: 'text-green-500',
          bgColor: 'bg-green-100',
          label: '✓ Active'
        };
      case 'completed':
        return {
          icon: CheckCircle2,
          color: 'text-purple-600',
          bgColor: 'bg-purple-100',
          label: '✓ Completed'
        };
      case 'initiating':
        return {
          icon: Loader2,
          color: 'text-blue-500',
          bgColor: 'bg-blue-100',
          label: '⟳ Initializing'
        };
      default:
        return {
          icon: CheckCircle2,
          color: 'text-gray-500',
          bgColor: 'bg-gray-100',
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