import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { randomRange } from '../utils/Random'
import { damp } from '../utils/Damp'

export class ThinkingLayer implements AnimationLayer {
  readonly name = 'ThinkingLayer'
  weight = 1

  private thinkingStartTime = 0
  private headTargetX = 0
  private headTargetY = 0
  private currentHeadX = 0
  private currentHeadY = 0
  private lookUp = 0
  private currentLookUp = 0
  private inhaleAmount = 0
  private currentInhale = 0
  private returning = false
  private offsets: Record<string, BoneTransform> = {}

  setWeight(weight: number): void {
    this.weight = weight
  }

  update(context: AnimationContext): void {
    if (context.state !== 'thinking') {
      this.currentHeadX = damp(this.currentHeadX, 0, 3, context.delta)
      this.currentHeadY = damp(this.currentHeadY, 0, 3, context.delta)
      this.currentLookUp = damp(this.currentLookUp, 0, 3, context.delta)
      this.currentInhale = damp(this.currentInhale, 0, 2, context.delta)
      this.returning = false
      this.offsets = {}
      return
    }

    if (!this.returning) {
      this.thinkingStartTime += context.delta

      this.headTargetX = CONFIG.Thinking.HeadTurnAngle * (Math.random() > 0.5 ? 1 : -1)
      this.headTargetY = CONFIG.Thinking.HeadTurnAngle * 0.3 * (Math.random() > 0.5 ? 1 : -1)
      this.lookUp = CONFIG.Thinking.LookUpAngle
      this.inhaleAmount = CONFIG.Thinking.InhaleAmount

      const returnTime = randomRange(CONFIG.Thinking.MinDuration, CONFIG.Thinking.MaxDuration)
      if (this.thinkingStartTime > returnTime) {
        this.returning = true
      }
    }

    if (this.returning) {
      this.currentHeadX = damp(this.currentHeadX, 0, 2.5, context.delta)
      this.currentHeadY = damp(this.currentHeadY, 0, 2.5, context.delta)
      this.currentLookUp = damp(this.currentLookUp, 0, 2.5, context.delta)
      this.currentInhale = damp(this.currentInhale, 0, 2, context.delta)
    } else {
      this.currentHeadX = damp(this.currentHeadX, this.headTargetX, 2, context.delta)
      this.currentHeadY = damp(this.currentHeadY, this.headTargetY, 2, context.delta)
      this.currentLookUp = damp(this.currentLookUp, this.lookUp, 2, context.delta)
      this.currentInhale = damp(this.currentInhale, this.inhaleAmount, 1.5, context.delta)
    }

    this.offsets = {
      head: { rotation: [this.currentLookUp, this.currentHeadY, this.currentHeadX] },
      spine: { rotation: [this.currentInhale, 0, 0] },
      spine1: { rotation: [this.currentInhale * 0.5, 0, 0] },
    }
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
