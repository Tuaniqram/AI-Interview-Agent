interface Props {
  radius: number;
  color?: string;
  opacity?: number;
  dashPattern?: string;
  duration?: number;
  reverse?: boolean;
  className?: string;
}

export function SegmentRing({ radius, color = '#5DE4FF', opacity = 0.1, dashPattern, duration = 24, reverse, className }: Props) {
  const dash = dashPattern || '15 5 8 5 25 8 6 8';

  return (
    <g>
      {/* Main ring */}
      <circle
        className={`seg-ring ${reverse ? 'reverse' : ''} ${className || ''}`}
        cx="160" cy="160" r={radius}
        fill="none" stroke={color} strokeWidth="0.5"
        strokeDasharray={dash}
        strokeLinecap="butt"
        opacity={opacity}
        style={{ ['--dur-seg' as string]: `${duration}s` }}
      />
      {/* Glow copy — counter-rotates for depth */}
      <circle
        className="seg-ring reverse"
        cx="160" cy="160" r={radius}
        fill="none" stroke={color} strokeWidth="1.5"
        strokeDasharray={dash}
        strokeLinecap="butt"
        opacity={opacity * 0.3}
        filter="url(#softGlow)"
        style={{ ['--dur-seg' as string]: `${duration * 1.6}s` }}
      />
    </g>
  );
}
