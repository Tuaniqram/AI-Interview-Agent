export type AuraState = 'idle' | 'listening' | 'thinking' | 'responding';

export interface AuraCoreProps {
  state?: AuraState;
  size?: number;
  className?: string;
}

export interface OrbitalRingProps {
  radius: number;
  strokeWidth: number;
  opacity: number;
  color: string;
  duration: number;
  reverse?: boolean;
  dashArray?: string;
}

export interface ParticleData {
  id: number;
  baseAngle: number;
  baseDistance: number;
  size: number;
  driftAmplitude: number;
  opacity: number;
  color: string;
}
