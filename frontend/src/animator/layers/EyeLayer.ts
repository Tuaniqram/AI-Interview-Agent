import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { randomRange } from '../utils/Random'
import { damp } from '../utils/Damp'

interface SaccadeState {
  targetX: number
  targetY: number
  currentX: number
  currentY: number
  holdTime: number
  elapsed: number
}

export class EyeLayer implements AnimationLayer {
  readonly name = 'EyeLayer'
  weight = 1

  private leftEye: SaccadeState = {
    targetX: 0, targetY: 0, currentX: 0, currentY: 0,
    holdTime: randomRange(CONFIG.Eye.SaccadeMinInterval, CONFIG.Eye.SaccadeMaxInterval),
    elapsed: 0,
  }
  private rightEye: SaccadeState = {
    targetX: 0, targetY: 0, currentX: 0, currentY: 0,
    holdTime: randomRange(CONFIG.Eye.SaccadeMinInterval, CONFIG.Eye.SaccadeMaxInterval),
    elapsed: 0,
  }

  private offsets: Record<string, BoneTransform> = {}

  update(context: AnimationContext): void {
    this.updateEye(this.leftEye, context.delta)
    this.updateEye(this.rightEye, context.delta)

    this.offsets = {
      leftEye: { rotation: [this.leftEye.currentX, this.leftEye.currentY, 0] },
      rightEye: { rotation: [this.rightEye.currentX, this.rightEye.currentY, 0] },
    }
  }

  private updateEye(eye: SaccadeState, delta: number): void {
    eye.elapsed += delta

    if (eye.elapsed >= eye.holdTime) {
      eye.targetX = randomRange(-CONFIG.Eye.SaccadeMagnitude, CONFIG.Eye.SaccadeMagnitude)
      eye.targetY = randomRange(-CONFIG.Eye.SaccadeMagnitude * 0.7, CONFIG.Eye.SaccadeMagnitude * 0.7)
      eye.holdTime = randomRange(CONFIG.Eye.SaccadeMinInterval, CONFIG.Eye.SaccadeMaxInterval)
      eye.elapsed = 0
    }

    eye.currentX = damp(eye.currentX, eye.targetX, 15, delta)
    eye.currentY = damp(eye.currentY, eye.targetY, 15, delta)
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
