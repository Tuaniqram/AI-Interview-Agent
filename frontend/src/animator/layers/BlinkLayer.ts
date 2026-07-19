import type { AnimationContext, AnimationLayer, BlinkType } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { randomRange, randomBool } from '../utils/Random'

export class BlinkLayer implements AnimationLayer {
  readonly name = 'BlinkLayer'
  weight = 1

  private timeToNextBlink = randomRange(CONFIG.Blink.MinInterval, CONFIG.Blink.MaxInterval)
  private blinkTimer = 0
  private blinking = false
  private blinkType: BlinkType = 'single'
  private blinkProgress = 0
  private morphInfluence = 0

  private offsets: Record<string, BoneTransform> = {}

  update(context: AnimationContext): void {
    if (!this.blinking) {
      this.timeToNextBlink -= context.delta
      if (this.timeToNextBlink <= 0) {
        this.startBlink()
      }
      this.morphInfluence = 0
      this.offsets = {}
      return
    }

    this.blinkTimer += context.delta
    this.updateBlink()

    if (this.blinkProgress >= 1) {
      this.blinking = false
      this.timeToNextBlink = randomRange(CONFIG.Blink.MinInterval, CONFIG.Blink.MaxInterval)
    }
  }

  private startBlink(): void {
    this.blinking = true
    this.blinkTimer = 0
    this.blinkProgress = 0

    if (randomBool(CONFIG.Blink.SlowBlinkProbability)) {
      this.blinkType = 'slow'
    } else if (randomBool(CONFIG.Blink.DoubleBlinkProbability)) {
      this.blinkType = 'double'
    } else {
      this.blinkType = 'single'
    }
  }

  private updateBlink(): void {
    const blinkDuration = this.blinkType === 'slow'
      ? CONFIG.Blink.SlowBlinkDuration
      : CONFIG.Blink.Duration

    if (this.blinkType === 'double') {
      const singleDuration = CONFIG.Blink.Duration
      const gap = CONFIG.Blink.DoubleBlinkGap
      const totalDoubleDuration = singleDuration * 2 + gap

      this.blinkProgress = this.blinkTimer / totalDoubleDuration

      if (this.blinkTimer < singleDuration) {
        this.morphInfluence = this.blinkTimer / singleDuration
      } else if (this.blinkTimer < singleDuration + gap) {
        this.morphInfluence = 1 - (this.blinkTimer - singleDuration) / gap
        this.morphInfluence = Math.max(0, this.morphInfluence)
      } else if (this.blinkTimer < singleDuration * 2 + gap) {
        const t = (this.blinkTimer - singleDuration - gap) / singleDuration
        this.morphInfluence = Math.min(1, t)
      } else {
        this.morphInfluence = 0
        this.blinkProgress = 1
      }
    } else {
      this.blinkProgress = this.blinkTimer / blinkDuration
      this.morphInfluence = this.blinkTimer < blinkDuration * 0.5
        ? this.blinkTimer / (blinkDuration * 0.5)
        : 1 - (this.blinkTimer - blinkDuration * 0.5) / (blinkDuration * 0.5)
      this.morphInfluence = Math.max(0, Math.min(1, this.morphInfluence))
    }
  }

  getBlinkInfluence(): number {
    return this.morphInfluence
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
