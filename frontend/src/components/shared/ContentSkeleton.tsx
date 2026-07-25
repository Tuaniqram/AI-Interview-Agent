import { Loader2 } from 'lucide-react';

export function ContentSkeleton() {
  return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="w-6 h-6 animate-spin text-action-primary" />
    </div>
  );
}
