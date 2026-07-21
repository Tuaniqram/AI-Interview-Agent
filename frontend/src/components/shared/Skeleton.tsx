interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circle' | 'rect';
  width?: string | number;
  height?: string | number;
}

export function Skeleton({ className = '', variant = 'text', width, height }: SkeletonProps) {
  const base = 'animate-pulse bg-elevated';
  const shape = variant === 'circle' ? 'rounded-full' : variant === 'rect' ? 'rounded-lg' : 'rounded h-4';

  return (
    <div
      className={`${base} ${shape} ${className}`}
      style={{ width, height }}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-elevated rounded-xl p-4 space-y-3">
      <Skeleton width="60%" />
      <Skeleton width="40%" height="2rem" />
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} width="100%" height="2.5rem" variant="rect" />
      ))}
    </div>
  );
}
