interface Props {
  radius: number;
  strokeWidth: number;
  opacity: number;
  color: string;
  duration: number;       // seconds per full rotation
  reverse?: boolean;
  dashArray?: string;
  className?: string;
}

export function OrbitalRing({ radius, strokeWidth, opacity, color, duration, reverse, dashArray, className }: Props) {
  return (
    <circle
      className={`ring ${reverse ? 'reverse' : ''} ${className || ''}`}
      cx="160"
      cy="160"
      r={radius}
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeDasharray={dashArray || undefined}
      strokeLinecap="round"
      opacity={opacity}
      style={{ ['--dur-r' as string]: `${duration}s` }}
    />
  );
}
