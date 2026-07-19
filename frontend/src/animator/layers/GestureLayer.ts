import type { AnimationContext, AnimationLayer, GestureType, GestureState, GestureDefinition, BoneTransform } from '../types'
import { smoothstep, damp } from '../utils/Damp'

const GESTURES: Record<GestureType, GestureDefinition> = {
  openPalm: {
    name: 'openPalm', arm: 'right',
    phases: [
      { duration: 0.3, targets: { rightForeArm: { rotation: [0, 0, -0.3] }, rightArm: { rotation: [0, 0, 0.06] } } },
      { duration: 0.6, targets: { rightForeArm: { rotation: [0, 0, -0.3] }, rightArm: { rotation: [0, 0, 0.06] } } },
      { duration: 0.4, targets: { rightForeArm: { rotation: [0, 0, 0] }, rightArm: { rotation: [0, 0, 0] } } },
    ],
  },
  singleHandEmphasis: {
    name: 'singleHandEmphasis', arm: 'right',
    phases: [
      { duration: 0.25, targets: { rightArm: { rotation: [-0.15, 0, 0.06] }, rightForeArm: { rotation: [0.1, 0, -0.15] } } },
      { duration: 0.5, targets: { rightArm: { rotation: [-0.15, 0, 0.06] }, rightForeArm: { rotation: [0.1, 0, -0.15] } } },
      { duration: 0.35, targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
  bothHandsOpen: {
    name: 'bothHandsOpen', arm: 'both',
    phases: [
      { duration: 0.35, targets: { leftArm: { rotation: [-0.08, 0, -0.06] }, rightArm: { rotation: [-0.08, 0, 0.06] } } },
      { duration: 0.5, targets: { leftArm: { rotation: [-0.08, 0, -0.06] }, rightArm: { rotation: [-0.08, 0, 0.06] } } },
      { duration: 0.4, targets: { leftArm: { rotation: [0, 0, 0] }, rightArm: { rotation: [0, 0, 0] } } },
    ],
  },
  forearmLift: {
    name: 'forearmLift', arm: 'right',
    phases: [
      { duration: 0.3, targets: { rightForeArm: { rotation: [0.25, 0, -0.3] } } },
      { duration: 0.4, targets: { rightForeArm: { rotation: [0.25, 0, -0.3] } } },
      { duration: 0.35, targets: { rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
  palmUpward: {
    name: 'palmUpward', arm: 'right',
    phases: [
      { duration: 0.3, targets: { rightForeArm: { rotation: [0.1, 0, -0.25] }, rightArm: { rotation: [0.05, 0, 0.04] } } },
      { duration: 0.5, targets: { rightForeArm: { rotation: [0.1, 0, -0.25] }, rightArm: { rotation: [0.05, 0, 0.04] } } },
      { duration: 0.35, targets: { rightForeArm: { rotation: [0, 0, 0] }, rightArm: { rotation: [0, 0, 0] } } },
    ],
  },
  smallPointing: {
    name: 'smallPointing', arm: 'right',
    phases: [
      { duration: 0.25, targets: { rightArm: { rotation: [-0.12, 0.04, 0.04] }, rightForeArm: { rotation: [0.15, 0, -0.12] } } },
      { duration: 0.5, targets: { rightArm: { rotation: [-0.12, 0.04, 0.04] }, rightForeArm: { rotation: [0.15, 0, -0.12] } } },
      { duration: 0.3, targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
  shoulderEmphasis: {
    name: 'shoulderEmphasis', arm: 'both',
    phases: [
      { duration: 0.3, targets: { leftShoulder: { rotation: [0, 0, 0.08] }, rightShoulder: { rotation: [0, 0, -0.08] } } },
      { duration: 0.4, targets: { leftShoulder: { rotation: [0, 0, 0.08] }, rightShoulder: { rotation: [0, 0, -0.08] } } },
      { duration: 0.35, targets: { leftShoulder: { rotation: [0, 0, 0] }, rightShoulder: { rotation: [0, 0, 0] } } },
    ],
  },
  chestEmphasis: {
    name: 'chestEmphasis', arm: 'right',
    phases: [
      { duration: 0.3, targets: { rightArm: { rotation: [0.08, -0.1, 0.04] }, rightForeArm: { rotation: [0.2, 0, -0.2] } } },
      { duration: 0.4, targets: { rightArm: { rotation: [0.08, -0.1, 0.04] }, rightForeArm: { rotation: [0.2, 0, -0.2] } } },
      { duration: 0.35, targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
  fingerEmphasis: {
    name: 'fingerEmphasis', arm: 'right',
    phases: [
      { duration: 0.2, targets: { rightForeArm: { rotation: [0.05, 0, -0.1] } } },
      { duration: 0.3, targets: { rightForeArm: { rotation: [0.05, 0, -0.1] } } },
      { duration: 0.2, targets: { rightForeArm: { rotation: [0, 0, 0] } } },
      { duration: 0.15, targets: { rightForeArm: { rotation: [0.03, 0, -0.06] } } },
      { duration: 0.2, targets: { rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
  handRotation: {
    name: 'handRotation', arm: 'right',
    phases: [
      { duration: 0.3, targets: { rightForeArm: { rotation: [0, -0.15, 0] } } },
      { duration: 0.4, targets: { rightForeArm: { rotation: [0, -0.15, 0] } } },
      { duration: 0.3, targets: { rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
  smallShrug: {
    name: 'smallShrug', arm: 'both',
    phases: [
      { duration: 0.4, targets: { leftShoulder: { rotation: [-0.08, 0, 0] }, rightShoulder: { rotation: [-0.08, 0, 0] } } },
      { duration: 0.5, targets: { leftShoulder: { rotation: [-0.08, 0, 0] }, rightShoulder: { rotation: [-0.08, 0, 0] } } },
      { duration: 0.4, targets: { leftShoulder: { rotation: [0, 0, 0] }, rightShoulder: { rotation: [0, 0, 0] } } },
    ],
  },
  questionEmphasis: {
    name: 'questionEmphasis', arm: 'right',
    phases: [
      { duration: 0.35, targets: { rightArm: { rotation: [0.06, 0, 0.08] }, head: { rotation: [0, 0, 0.05] }, rightForeArm: { rotation: [0, 0, -0.15] } } },
      { duration: 0.6, targets: { rightArm: { rotation: [0.06, 0, 0.08] }, head: { rotation: [0, 0, 0.05] }, rightForeArm: { rotation: [0, 0, -0.15] } } },
      { duration: 0.4, targets: { rightArm: { rotation: [0, 0, 0] }, head: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
  agreementNod: {
    name: 'agreementNod', arm: 'both',
    phases: [
      { duration: 0.2, targets: { head: { rotation: [0, 0, -0.06] } } },
      { duration: 0.15, targets: { head: { rotation: [0, 0, 0.03] } } },
      { duration: 0.2, targets: { head: { rotation: [0, 0, 0] } } },
    ],
  },
  explanationGesture: {
    name: 'explanationGesture', arm: 'right',
    phases: [
      { duration: 0.4, targets: { rightArm: { rotation: [-0.12, 0.06, 0.1] }, rightForeArm: { rotation: [0.2, 0, -0.25] } } },
      { duration: 0.6, targets: { rightArm: { rotation: [-0.12, 0.06, 0.1] }, rightForeArm: { rotation: [0.2, 0, -0.25] } } },
      { duration: 0.3, targets: { rightArm: { rotation: [-0.06, 0.03, 0.05] }, rightForeArm: { rotation: [0.1, 0, -0.12] } } },
      { duration: 0.3, targets: { rightArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
  closingGesture: {
    name: 'closingGesture', arm: 'both',
    phases: [
      { duration: 0.4, targets: { leftArm: { rotation: [0.06, 0.06, -0.06] }, rightArm: { rotation: [0.06, -0.06, 0.06] }, leftForeArm: { rotation: [0.1, 0, 0.1] }, rightForeArm: { rotation: [0.1, 0, -0.1] } } },
      { duration: 0.5, targets: { leftArm: { rotation: [0.06, 0.06, -0.06] }, rightArm: { rotation: [0.06, -0.06, 0.06] }, leftForeArm: { rotation: [0.1, 0, 0.1] }, rightForeArm: { rotation: [0.1, 0, -0.1] } } },
      { duration: 0.4, targets: { leftArm: { rotation: [0, 0, 0] }, rightArm: { rotation: [0, 0, 0] }, leftForeArm: { rotation: [0, 0, 0] }, rightForeArm: { rotation: [0, 0, 0] } } },
    ],
  },
}

export class GestureLayer implements AnimationLayer {
  readonly name = 'GestureLayer'
  weight = 1

  private currentGesture: GestureState | null = null
  private accumulatedOffsets: Record<string, BoneTransform> = {}
  private smoothingOffsets: Record<string, { current: [number, number, number]; velocity: [number, number, number] }> = {}

  triggerGesture(type: GestureType): void {
    if (this.currentGesture?.active) return

    const def = GESTURES[type]
    if (!def) return

    this.currentGesture = {
      active: true,
      type: type,
      phaseIndex: 0,
      phaseTime: 0,
      totalTime: 0,
      elapsed: 0,
    }
  }

  isAnyGestureActive(): boolean {
    return this.currentGesture?.active ?? false
  }

  update(context: AnimationContext): void {
    if (!this.currentGesture?.active) {
      this.accumulatedOffsets = {}
      return
    }

    const gesture = this.currentGesture
    const def = GESTURES[gesture.type!]
    if (!def) {
      this.currentGesture = null
      return
    }

    gesture.elapsed += context.delta
    gesture.phaseTime += context.delta

    const phase = def.phases[gesture.phaseIndex]
    if (!phase) {
      this.currentGesture = null
      this.accumulatedOffsets = {}
      return
    }

    const phaseProgress = Math.min(1, gesture.phaseTime / phase.duration)
    const eased = smoothstep(phaseProgress)

    const temp: Record<string, BoneTransform> = {}
    for (const [boneName, target] of Object.entries(phase.targets)) {
      const rot = target.rotation ?? [0, 0, 0]
      temp[boneName] = {
        rotation: [rot[0] * eased, rot[1] * eased, rot[2] * eased],
      }
    }

    if (phaseProgress >= 1) {
      gesture.phaseIndex++
      gesture.phaseTime = 0

      if (gesture.phaseIndex >= def.phases.length) {
        this.currentGesture = null
      }
    }

    for (const [boneName, transform] of Object.entries(temp)) {
      const existing = this.accumulatedOffsets[boneName]
      if (existing?.rotation) {
        const r = existing.rotation
        const tr = transform.rotation ?? [0, 0, 0]
        existing.rotation = [r[0] + tr[0], r[1] + tr[1], r[2] + tr[2]]
      } else {
        this.accumulatedOffsets[boneName] = {
          rotation: [...(transform.rotation ?? [0, 0, 0])],
        }
      }
    }

    if (!this.currentGesture) {
      this.scheduleReturnToNeutral(context.delta)
    }
  }

  private scheduleReturnToNeutral(delta: number): void {
    for (const [boneName] of Object.entries(this.accumulatedOffsets)) {
      if (!this.smoothingOffsets[boneName]) {
        this.smoothingOffsets[boneName] = {
          current: [0, 0, 0],
          velocity: [0, 0, 0],
        }
      }
      const smooth = this.smoothingOffsets[boneName]
      const acc = this.accumulatedOffsets[boneName]
      if (acc.rotation) {
        smooth.current[0] = damp(smooth.current[0], 0, 5, delta)
        smooth.current[1] = damp(smooth.current[1], 0, 5, delta)
        smooth.current[2] = damp(smooth.current[2], 0, 5, delta)
        acc.rotation = [smooth.current[0], smooth.current[1], smooth.current[2]]
      }
    }

    let allZero = true
    for (const [, s] of Object.entries(this.smoothingOffsets)) {
      if (Math.abs(s.current[0]) > 0.0001 || Math.abs(s.current[1]) > 0.0001 || Math.abs(s.current[2]) > 0.0001) {
        allZero = false
        break
      }
    }
    if (allZero) {
      this.accumulatedOffsets = {}
      this.smoothingOffsets = {}
    }
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.accumulatedOffsets
  }
}
