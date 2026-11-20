import { motion, AnimatePresence } from 'framer-motion';
import type { AuraCoreProps } from './types';
import { PlasmaNucleus } from './PlasmaNucleus';
import { GlowLayer } from './GlowLayer';
import { OrbitalRing } from './OrbitalRing';
import { SegmentRing } from './SegmentRing';
import { EnergyPulse } from './EnergyPulse';
import { ParticleField } from './ParticleField';
import './aura.css';

export function AuraCore({ state = 'idle', size = 320, className = '' }: AuraCoreProps) {
  return (
    <div
      className={`aura-root ${className}`}
      data-state={state}
      style={{ width: size, height: size, position: 'relative' }}
    >
      <svg
        viewBox="0 0 320 320"
        width={size}
        height={size}
        style={{ position: 'absolute', top: 0, left: 0 }}
      >
        <defs>
          <radialGradient id="nucleusGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#fff" stopOpacity="1" />
            <stop offset="15%" stopColor="#D8E7FF" stopOpacity="0.95" />
            <stop offset="35%" stopColor="#7C5CFF" stopOpacity="0.7" />
            <stop offset="60%" stopColor="#5DE4FF" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#7C5CFF" stopOpacity="0" />
          </radialGradient>

          <radialGradient id="nucleusInner" cx="38%" cy="38%" r="50%">
            <stop offset="0%" stopColor="#fff" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#7C5CFF" stopOpacity="0" />
          </radialGradient>

          <radialGradient id="glowInner" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#7C5CFF" stopOpacity="0.2" />
            <stop offset="40%" stopColor="#7C5CFF" stopOpacity="0.08" />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </radialGradient>

          <radialGradient id="glowMid" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#5DE4FF" stopOpacity="0.08" />
            <stop offset="50%" stopColor="#7C5CFF" stopOpacity="0.04" />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </radialGradient>

          <radialGradient id="glowOuter" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#7C5CFF" stopOpacity="0.05" />
            <stop offset="60%" stopColor="#5DE4FF" stopOpacity="0.02" />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </radialGradient>

          <filter id="nucleusGlow">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3" />
          </filter>

          <filter id="softGlow">
            <feGaussianBlur in="SourceGraphic" stdDeviation="8" />
          </filter>

          <filter id="wideGlow">
            <feGaussianBlur in="SourceGraphic" stdDeviation="16" />
          </filter>
        </defs>

        {/* LAYER 8: Background glow */}
        <GlowLayer />

        {/* LAYER 7: Energy pulses */}
        <EnergyPulse state={state} />

        {/* LAYER 6: Floating particles */}
        <ParticleField activity={1} />

        {/* LAYER 5: Orbital rings */}
        <OrbitalRing radius={148} strokeWidth={0.6} opacity={0.18} color="#5DE4FF" duration={30} dashArray="12 8 4 8" />
        <OrbitalRing radius={138} strokeWidth={0.7} opacity={0.22} color="#7C5CFF" duration={22} reverse dashArray="25 5 10 5 15 8" />
        <OrbitalRing radius={128} strokeWidth={0.8} opacity={0.25} color="#D8E7FF" duration={14} dashArray="40 6 8 6" />
        <OrbitalRing radius={118} strokeWidth={0.7} opacity={0.2} color="#7C5CFF" duration={10} reverse />
        <OrbitalRing radius={108} strokeWidth={0.5} opacity={0.15} color="#5DE4FF" duration={26} dashArray="8 12 20 8" />
        <OrbitalRing radius={98} strokeWidth={0.6} opacity={0.14} color="#D8E7FF" duration={18} reverse dashArray="15 5" />

        {/* LAYER 4: Segment rings */}
        <SegmentRing radius={158} color="#5DE4FF" opacity={0.1} duration={24} />
        <SegmentRing radius={88} color="#7C5CFF" opacity={0.08} duration={32} reverse dashPattern="18 4 6 4 12 6" />

        {/* State-specific rings (fade in/out via CSS) */}
        <circle
          className="focus-ring"
          cx="160" cy="160" r="60"
          fill="none"
          stroke="#5DE4FF"
          strokeWidth="0.8"
          strokeDasharray="10 6 3 6"
          style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
        />
        <circle
          className="surge-ring"
          cx="160" cy="160" r="150"
          fill="none"
          stroke="#7C5CFF"
          strokeWidth="1"
          strokeDasharray="30 14 8 14 50 14"
          style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
        />
        <circle
          className="settle-ring"
          cx="160" cy="160" r="130"
          fill="none"
          stroke="#D8E7FF"
          strokeWidth="0.6"
          style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
        />

        {/* LAYER 1: Plasma nucleus */}
        <PlasmaNucleus />

        {/* Responding: one-shot flash (Framer) */}
        <AnimatePresence>
          {state === 'responding' && (
            <motion.circle
              cx="160" cy="160" r="20"
              fill="none"
              stroke="#fff"
              strokeWidth="1.2"
              initial={{ r: 20, opacity: 0 }}
              animate={{ r: 70, opacity: [0, 0.9, 0] }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.7, times: [0, 0.3, 1], ease: 'easeInOut' }}
            />
          )}
        </AnimatePresence>
      </svg>
    </div>
  );
}