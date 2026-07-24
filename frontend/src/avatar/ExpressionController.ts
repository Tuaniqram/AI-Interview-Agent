import { damp } from '../animator/utils/Damp'
import type { AvatarEmotion } from '../types/avatar'

const EMOTION_MORPHS: Record<string, Record<string, number>> = {
  neutral: {},
  happy: {
    browInnerUp: 0.3,
    mouthSmile: 0.7,
    cheekSquint: 0.4,
    eyeBlink: 0.1,
  },
  thoughtful: {
    browDown: 0.3,
    eyeLookUp: 0.4,
    mouthStretch: 0.2,
    mouthPress: 0.3,
  },
  concerned: {
    browDown: 0.5,
    eyeSquint: 0.3,
    mouthPress: 0.3,
  },
  confident: {
    browInnerUp: 0.3,
    mouthSmile: 0.4,
    jawOpen: 0.1,
  },
  surprised: {
    browInnerUp: 0.8,
    eyeWide: 0.7,
    jawOpen: 0.5,
  },
  laughing: {
    mouthSmile: 0.7,
    cheekSquint: 0.5,
    jawOpen: 0.3,
    eyeBlink: 0.2,
  },
  considering: {
    browDown: 0.4,
    eyeSquint: 0.3,
    mouthPress: 0.2,
  },
  excited: {
    browInnerUp: 0.6,
    eyeWide: 0.5,
    mouthSmile: 0.6,
    jawOpen: 0.2,
  },
}

export class ExpressionController {
  private currentEmotion: AvatarEmotion = 'neutral'
  private targetEmotion: AvatarEmotion = 'neutral'
  private emotionWeight = 0
  private currentMorphs: Record<string, number> = {}

  setEmotion(emotion: AvatarEmotion, weight = 1): void {
    this.targetEmotion = emotion
    this.emotionWeight = weight
  }

  update(delta: number, _lipSyncActive: boolean): Record<string, number> {
    if (this.currentEmotion !== this.targetEmotion) {
      this.currentEmotion = this.targetEmotion
    }

    const targetMorphs = EMOTION_MORPHS[this.currentEmotion] ?? {}
    const result: Record<string, number> = {}

    for (const [key, val] of Object.entries(targetMorphs)) {
      const current = this.currentMorphs[key] ?? 0
      const damped = damp(current, val * this.emotionWeight, 5, delta)
      result[key] = damped
      this.currentMorphs[key] = damped
    }

    return result
  }

  get emotion(): AvatarEmotion {
    return this.currentEmotion
  }

  reset(): void {
    this.currentEmotion = 'neutral'
    this.targetEmotion = 'neutral'
    this.emotionWeight = 0
    this.currentMorphs = {}
  }
}
