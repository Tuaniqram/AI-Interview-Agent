import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import type { AuraState } from './types';

interface Props { state: AuraState }

const stateInterval: Record<AuraState, [number, number]> = {
  idle: [2600, 4500],
  listening: [2000, 3500],
  thinking: [1200, 2200],
  responding: [0, 0],
};

export function EnergyPulse({ state }: Props) {
  const [pulseKey, setPulseKey] = useState(0);

  useEffect(() => {
    if (state === 'responding') {
      setPulseKey(k => k + 1);
      return;
    }

    const [min, max] = stateInterval[state];
    if (min === 0) return;

    const interval = min + Math.random() * (max - min);
    const timer = setTimeout(() => {
      setPulseKey(k => k + 1);
    }, interval);

    return () => clearTimeout(timer);
  }, [state, pulseKey]);

  return (
    <g key={`pulse-${pulseKey}`}>
      {[0, 0.5, 1].map((delay, i) => (
        <motion.circle
          key={i}
          cx="160" cy="160" r="28"
          fill="none"
          stroke="#7C5CFF"
          strokeWidth="0.7"
          initial={{ r: 28, opacity: 0 }}
          animate={{ r: 155, opacity: [0, 0.5, 0] }}
          transition={{
            duration: 2.4,
            delay,
            times: [0, 0.25, 1],
            ease: 'easeInOut',
          }}
        />
      ))}
      <motion.circle
        cx="160" cy="160" r="28"
        fill="none"
        stroke="#5DE4FF"
        strokeWidth="0.4"
        initial={{ r: 28, opacity: 0 }}
        animate={{ r: 140, opacity: [0, 0.3, 0] }}
        transition={{
          duration: 2,
          delay: 0.2,
          times: [0, 0.25, 1],
          ease: 'easeInOut',
        }}
      />
    </g>
  );
}
