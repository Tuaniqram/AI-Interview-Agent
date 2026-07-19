import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { randomRange } from '../utils/Random'
import { damp } from '../utils/Damp'

export class ListeningLayer implements AnimationLayer {
  readonly name = 'ListeningLayer'
  weight = 1

  private timeToNextNod = randomRange(CONFIG.Listening.NodMinInterval, CONFIG.Listening.NodMaxInterval)
  private nodding = false
  private nodTime = 0
  private nodValue = 0
  private leanForward = 0
  private headTilt = 0
  private offsets: Record<string, BoneTransform> = {}

  setWeight(weight: number): void {
    this.weight = weight
  }

  update(context: AnimationContext): void {
    if (context.state !== 'listening') {
      this.offsets = {}
      this.nodding = false
      this.nodValue = damp(this.nodValue, 0, 3, context.delta)
      return
    }

    this.leanForward = CONFIG.Listening.LeanForwardAngle
    this.headTilt = CONFIG.Listening.HeadTiltAngle

    this.timeToNextNod -= context.delta
    if (this.timeToNextNod <= 0 && !this.nodding) {
      this.nodding = true
      this.nodTime = 0
      this.timeToNextNod = randomRange(CONFIG.Listening.NodMinInterval, CONFIG.Listening.NodMaxInterval)
    }

    if (this.nodding) {
      this.nodTime += context.delta
      const t = Math.min(1, this.nodTime / 0.5)
      this.nodValue = Math.sin(t * Math.PI) * CONFIG.Listening.NodAmount
      if (t >= 1) {
        this.nodding = false
        this.nodValue = 0
      }
    } else {
      this.nodValue = damp(this.nodValue, 0, 4, context.delta)
    }

    this.offsets = {
      spine: { rotation: [this.leanForward, 0, 0] },
      spine1: { rotation: [this.leanForward * 0.6, 0, 0] },
      head: { rotation: [0, 0, this.headTilt + this.nodValue] },
    }
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
