import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { randomRange } from '../utils/Random'
import { damp } from '../utils/Damp'

export class WeightShiftLayer implements AnimationLayer {
  readonly name = 'WeightShiftLayer'
  weight = 1

  private dominantSide: 'left' | 'right' = 'left'
  private timeToNext = randomRange(
    CONFIG.WeightShift.IntervalMin,
    CONFIG.WeightShift.IntervalMax,
  )
  private shifting = false
  private shiftTime = 0
  private targetShoulderDrop = 0
  private currentShoulderDrop = 0
  private targetSpineShift = 0
  private currentSpineShift = 0
  private offsets: Record<string, BoneTransform> = {}

  update(context: AnimationContext): void {
    this.timeToNext -= context.delta

    if (this.timeToNext <= 0 && !this.shifting) {
      this.startShift()
    }

    if (this.shifting) {
      this.shiftTime += context.delta
      const progress = Math.min(1, this.shiftTime / CONFIG.WeightShift.ShiftDuration)

      this.currentShoulderDrop = damp(
        this.currentShoulderDrop,
        this.targetShoulderDrop,
        4,
        context.delta,
      )
      this.currentSpineShift = damp(
        this.currentSpineShift,
        this.targetSpineShift,
        4,
        context.delta,
      )

      if (progress >= 1) {
        this.shifting = false
        this.timeToNext = randomRange(
          CONFIG.WeightShift.IntervalMin,
          CONFIG.WeightShift.IntervalMax,
        )
      }
    }

    const leftDrop = this.dominantSide === 'left' ? this.currentShoulderDrop : -this.currentShoulderDrop * 0.7
    const rightDrop = this.dominantSide === 'right' ? this.currentShoulderDrop : -this.currentShoulderDrop * 0.7

    this.offsets = {
      leftShoulder: { rotation: [0, 0, leftDrop] },
      rightShoulder: { rotation: [0, 0, rightDrop] },
      spine: { rotation: [0, this.currentSpineShift, 0] },
    }
  }

  private startShift(): void {
    this.shifting = true
    this.shiftTime = 0
    this.dominantSide = Math.random() > 0.5 ? 'left' : 'right'
    this.targetShoulderDrop = randomRange(
      -CONFIG.WeightShift.ShoulderDropAmount,
      CONFIG.WeightShift.ShoulderDropAmount,
    )
    this.targetSpineShift = randomRange(
      -CONFIG.WeightShift.SpineShiftAmount,
      CONFIG.WeightShift.SpineShiftAmount,
    )
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
