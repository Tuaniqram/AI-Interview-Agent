import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { damp } from '../utils/Damp'
import { randomRange } from '../utils/Random'

export class IdleLayer implements AnimationLayer {
  readonly name = 'IdleLayer'
  weight = 1

  private timeToHeadCorrection = randomRange(15, 45)
  private headCorrecting = false
  private headTarget: [number, number, number] = [0, 0, 0]
  private headCurrent: [number, number, number] = [0, 0, 0]
  private offsets: Record<string, BoneTransform> = {}

  update(context: AnimationContext): void {
    if (context.state !== 'idle') {
      this.offsets = {}
      return
    }

    this.timeToHeadCorrection -= context.delta
    if (this.timeToHeadCorrection <= 0 && !this.headCorrecting) {
      this.headCorrecting = true
      this.headTarget = [
        randomRange(-0.01, 0.01),
        randomRange(-0.015, 0.015),
        randomRange(-0.005, 0.005),
      ]
    }

    if (this.headCorrecting) {
      this.headCurrent[0] = damp(this.headCurrent[0], this.headTarget[0], 1.5, context.delta)
      this.headCurrent[1] = damp(this.headCurrent[1], this.headTarget[1], 1.5, context.delta)
      this.headCurrent[2] = damp(this.headCurrent[2], this.headTarget[2], 1.5, context.delta)

      const diff = Math.abs(this.headCurrent[0] - this.headTarget[0]) +
                   Math.abs(this.headCurrent[1] - this.headTarget[1]) +
                   Math.abs(this.headCurrent[2] - this.headTarget[2])

      if (diff < 0.001) {
        this.headCorrecting = false
        this.timeToHeadCorrection = randomRange(15, 45)
        this.headTarget = [0, 0, 0]
      }
    } else {
      this.headCurrent[0] = damp(this.headCurrent[0], 0, 0.5, context.delta)
      this.headCurrent[1] = damp(this.headCurrent[1], 0, 0.5, context.delta)
      this.headCurrent[2] = damp(this.headCurrent[2], 0, 0.5, context.delta)
    }

    this.offsets = {
      head: { rotation: [this.headCurrent[0], this.headCurrent[1], this.headCurrent[2]] },
    }
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
