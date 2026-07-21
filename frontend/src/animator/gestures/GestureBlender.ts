import { MathUtils } from 'three'
import type { EasingType, GestureBoneTarget, GestureDefinition } from './GestureTypes'

const DEBUG_GESTURES = typeof window !== 'undefined' && (window as any).DEBUG_GESTURES === true

export function debugGesture(...args: unknown[]): void {
  if (DEBUG_GESTURES) {
    console.log('[GESTURE]', ...args)
  }
}

export function easeInOut(t: number): number {
  return MathUtils.smoothstep(t, 0, 1)
}

export function easeIn(t: number): number {
  return t * t
}

export function easeOut(t: number): number {
  return t * (2 - t)
}

export function easeOutBack(t: number): number {
  const c1 = 1.70158
  const c3 = c1 + 1
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
}

export function applyEasing(t: number, easing?: EasingType): number {
  switch (easing ?? 'easeInOut') {
    case 'linear': return t
    case 'easeIn': return easeIn(t)
    case 'easeOut': return easeOut(t)
    case 'easeInOut': return easeInOut(t)
    case 'easeOutBack': return easeOutBack(t)
    default: return easeInOut(t)
  }
}

export function computePhaseTargets(
  phase: { duration: number; targets: Record<string, GestureBoneTarget>; easing?: EasingType },
  phaseProgress: number,
): Record<string, GestureBoneTarget> {
  const eased = applyEasing(Math.min(1, phaseProgress), phase.easing)
  const result: Record<string, GestureBoneTarget> = {}

  for (const [boneName, target] of Object.entries(phase.targets)) {
    const rot = target.rotation ?? [0, 0, 0]
    result[boneName] = {
      rotation: [rot[0] * eased, rot[1] * eased, rot[2] * eased],
      ...(target.position ? { position: target.position.map(v => v * eased) as [number, number, number] } : {}),
    }
  }

  return result
}

export function damp(
  current: number,
  target: number,
  lambda: number,
  delta: number,
): number {
  return current + (target - current) * (1 - Math.exp(-lambda * delta))
}

export function getPhaseLabel(index: number, totalPhases: number): string {
  if (totalPhases <= 0) return 'idle'
  const labels = ['anticipation', 'attack', 'hold', 'release', 'followThrough']
  return labels[index] ?? `phase_${index}`
}

export function createFallbackTargets(
  def: GestureDefinition,
  availableBones: Set<string>,
): GestureDefinition {
  const hasLeftShoulder = availableBones.has('leftShoulder')
  const hasRightShoulder = availableBones.has('rightShoulder')

  const needsFixing = !hasLeftShoulder || !hasRightShoulder ||
    Object.keys(def.phases[0]?.targets ?? {}).some(k =>
      k.includes('Shoulder') && !availableBones.has(k),
    )

  if (!needsFixing) return def

  if (!hasLeftShoulder || !hasRightShoulder) {
    console.warn(`[GestureBlender] Shoulder bones missing for "${def.name}" — remapping shoulder to arm`)
  }

  const fixed: GestureDefinition = {
    ...def,
    phases: def.phases.map(phase => {
      const targets: Record<string, GestureBoneTarget> = {}
      for (const [boneName, target] of Object.entries(phase.targets)) {
        if (boneName === 'leftShoulder' && !hasLeftShoulder) {
          if (!targets['leftArm']) targets['leftArm'] = { rotation: [0, 0, 0] }
          const existing = targets['leftArm'].rotation ?? [0, 0, 0]
          targets['leftArm'] = {
            rotation: [
              existing[0] + (target.rotation?.[0] ?? 0) * 0.5,
              existing[1] + (target.rotation?.[1] ?? 0) * 0.5,
              existing[2] + (target.rotation?.[2] ?? 0) * 0.5,
            ],
          }
        } else if (boneName === 'rightShoulder' && !hasRightShoulder) {
          if (!targets['rightArm']) targets['rightArm'] = { rotation: [0, 0, 0] }
          const existing = targets['rightArm'].rotation ?? [0, 0, 0]
          targets['rightArm'] = {
            rotation: [
              existing[0] + (target.rotation?.[0] ?? 0) * 0.5,
              existing[1] + (target.rotation?.[1] ?? 0) * 0.5,
              existing[2] + (target.rotation?.[2] ?? 0) * 0.5,
            ],
          }
        } else if (boneName.includes('Finger') && !availableBones.has(boneName)) {
          const side = boneName.startsWith('left') ? 'left' : 'right'
          const handBone = side === 'left' ? 'leftHand' : 'rightHand'
          if (!targets[handBone]) targets[handBone] = { rotation: [0, 0, 0] }
          const existing = targets[handBone].rotation ?? [0, 0, 0]
          targets[handBone] = {
            rotation: [
              existing[0] + (target.rotation?.[0] ?? 0),
              existing[1] + (target.rotation?.[1] ?? 0),
              existing[2] + (target.rotation?.[2] ?? 0),
            ],
          }
        } else {
          targets[boneName] = target
        }
      }
      return { ...phase, targets }
    }),
  }

  return fixed
}
