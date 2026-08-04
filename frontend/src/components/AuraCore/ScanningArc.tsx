import { motion } from 'framer-motion';
import type { AuraState } from './types';

interface Props {
  radius: number;
  arcLength: number;
  speed: number;
  state: AuraState;
  delay?: number;
  color?: string;
}

const stateSpeed: Record<AuraState, number> = {
  idle: 1,
  listening: 1.3,
  thinking: 3,
  responding: 1.5,
};

export function ScanningArc({ radius, arcLength, speed, state, delay = 0, color = '#7C5CFF' }: Props) {
  const duration = speed / stateSpeed[state];
  const circumference = 2 * Math.PI * radius;
  const dashLen = (arcLength / 360) * circumference;
  const gapLen = circumference - dashLen;

  return (
    <g>
      {/* Arc trail */}
      <motion.circle
        cx="160" cy="160" r={radius}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeDasharray={`${dashLen} ${gapLen}`}
        strokeLinecap="round"
        opacity={0.4}
        filter="url(#softGlow)"
        animate={{ rotate: [0, 360] }}
        transition={{
          duration,
          repeat: Infinity,
          ease: 'linear',
          delay,
        }}
        style={{ transformOrigin: '160px 160px' }}
      />
      {/* Bright head */}
      <motion.circle
        cx="160" cy="160" r={radius}
        fill="none"
        stroke="#fff"
        strokeWidth="1"
        strokeDasharray={`${dashLen * 0.3} ${gapLen + dashLen * 0.7}`}
        strokeLinecap="round"
        opacity={0.6}
        animate={{ rotate: [0, 360] }}
        transition={{
          duration,
          repeat: Infinity,
          ease: 'linear',
          delay,
        }}
        style={{ transformOrigin: '160px 160px' }}
      />
    </g>
  );
}
