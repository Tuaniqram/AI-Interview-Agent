import { useMemo } from 'react';
import type { ParticleData } from './types';

const COLORS = ['#7C5CFF', '#5DE4FF', '#D8E7FF'];

function generateParticles(count: number): ParticleData[] {
  return Array.from({ length: count }, (_, i) => {
    const angle = Math.random() * Math.PI * 2;
    const dist = 88 + Math.random() * 70;
    return {
      id: i,
      baseAngle: angle,
      baseDistance: dist,
      size: 1 + Math.random() * 2,
      orbitSpeed: 14 + Math.random() * 22,
      driftAmplitude: 10 + Math.random() * 22,
      driftSpeed: 3 + Math.random() * 4,
      opacity: 0.35 + Math.random() * 0.45,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
    };
  });
}

interface Props {
  activity?: number;
}

export function ParticleField({ activity: _activity }: Props) {
  const particles = useMemo(() => generateParticles(32), []);

  return (
    <g>
      {particles.map((p, i) => {
        const x = 160 + Math.cos(p.baseAngle) * p.baseDistance;
        const y = 160 + Math.sin(p.baseAngle) * p.baseDistance;
        const dx = Math.cos(p.baseAngle + 1.2) * p.driftAmplitude;
        const dy = Math.sin(p.baseAngle + 1.2) * p.driftAmplitude;
        const isTwin = i % 5 === 0;

        return (
          <circle
            key={p.id}
            className={`particle ${isTwin ? 'twin' : ''}`}
            cx={x}
            cy={y}
            r={p.size}
            fill={p.color}
            opacity={p.opacity}
            style={{
              ['--dx' as string]: `${dx}px`,
              ['--dy' as string]: `${dy}px`,
              animationDelay: `${(p.id % 7) * 0.4}s`,
            }}
          />
        );
      })}
    </g>
  );
}