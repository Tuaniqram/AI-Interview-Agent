import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { randomRange } from '../utils/Random'
import { damp } from '../utils/Damp'

export class PostureLayer implements AnimationLayer {
  readonly name = 'PostureLayer'
  weight = 1

  private timeToNext = randomRange(
    CONFIG.Posture.AdjustmentIntervalMin,
    CONFIG.Posture.AdjustmentIntervalMax,
  )
  private adjusting = false
  private adjustTime = 0
  private adjustDuration = 2
  private targetSpine: [number, number, number] = [0, 0, 0]
  private currentSpine: [number, number, number] = [0, 0, 0]
  private targetShoulder: [number, number, number] = [0, 0, 0]
  private currentShoulder: [number, number, number] = [0, 0, 0]
  private offsets: Record<string, BoneTransform> = {}

  update(context: AnimationContext): void {
    this.timeToNext -= context.delta

    if (this.timeToNext <= 0 && !this.adjusting) {
      this.startAdjustment()
    }

    if (this.adjusting) {
      this.adjustTime += context.delta
      const progress = Math.min(1, this.adjustTime / this.adjustDuration)

      this.currentSpine[0] = damp(this.currentSpine[0], this.targetSpine[0], 3, context.delta)
      this.currentSpine[1] = damp(this.currentSpine[1], this.targetSpine[1], 3, context.delta)
      this.currentSpine[2] = damp(this.currentSpine[2], this.targetSpine[2], 3, context.delta)
      this.currentShoulder[0] = damp(this.currentShoulder[0], this.targetShoulder[0], 3, context.delta)
      this.currentShoulder[1] = damp(this.currentShoulder[1], this.targetShoulder[1], 3, context.delta)
      this.currentShoulder[2] = damp(this.currentShoulder[2], this.targetShoulder[2], 3, context.delta)

      if (progress >= 1) {
        this.adjusting = false
        this.timeToNext = randomRange(
          CONFIG.Posture.AdjustmentIntervalMin,
          CONFIG.Posture.AdjustmentIntervalMax,
        )
      }
    }

    this.offsets = {
      spine: { rotation: [this.currentSpine[0], this.currentSpine[1], this.currentSpine[2]] },
      leftShoulder: { rotation: [this.currentShoulder[0], this.currentShoulder[1], this.currentShoulder[2]] },
      rightShoulder: { rotation: [-this.currentShoulder[0], this.currentShoulder[1], -this.currentShoulder[2]] },
    }
  }

  private startAdjustment(): void {
    this.adjusting = true
    this.adjustTime = 0
    this.adjustDuration = randomRange(1.5, 3)
    this.targetSpine = [
      randomRange(-CONFIG.Posture.SpineCorrectionAmount, CONFIG.Posture.SpineCorrectionAmount) * 0.3,
      0,
      randomRange(0, CONFIG.Posture.TorsoStraightenAmount),
    ]
    this.targetShoulder = [
      randomRange(-CONFIG.Posture.ShoulderRelaxAmount, CONFIG.Posture.ShoulderRelaxAmount) * 0.5,
      0,
      0,
    ]
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
