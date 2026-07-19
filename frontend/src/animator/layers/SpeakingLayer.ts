import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform, GestureType } from '../types'
import { CONFIG } from '../utils/Config'
import { randomRange } from '../utils/Random'
import { damp } from '../utils/Damp'
import { GestureLayer } from './GestureLayer'

const GESTURE_LIST: GestureType[] = [
  'openPalm', 'singleHandEmphasis', 'bothHandsOpen', 'forearmLift',
  'palmUpward', 'smallPointing', 'shoulderEmphasis', 'chestEmphasis',
  'fingerEmphasis', 'handRotation', 'smallShrug', 'questionEmphasis',
  'explanationGesture', 'closingGesture',
]

export class SpeakingLayer implements AnimationLayer {
  readonly name = 'SpeakingLayer'
  weight = 1

  private gestureCooldown = 0
  private gestureTimestamps: number[] = []
  private gestureLayer: GestureLayer
  private headEmphasis: [number, number, number] = [0, 0, 0]
  private currentHeadEmphasis: [number, number, number] = [0, 0, 0]
  private postureForward = 0
  private timeSinceLastHeadNod = 0
  private elapsed = 0
  private offsets: Record<string, BoneTransform> = {}

  constructor(gestureLayer: GestureLayer) {
    this.gestureLayer = gestureLayer
  }

  setWeight(weight: number): void {
    this.weight = weight
  }

  private getRecentGestureCount(): number {
    const cutoff = this.elapsed - 60
    this.gestureTimestamps = this.gestureTimestamps.filter(t => t > cutoff)
    return this.gestureTimestamps.length
  }

  update(context: AnimationContext): void {
    if (context.state !== 'speaking') {
      this.offsets = {}
      this.gestureCooldown = 0
      this.gestureTimestamps = []
      this.elapsed = 0
      return
    }

    this.elapsed += context.delta
    this.gestureCooldown -= context.delta
    this.timeSinceLastHeadNod += context.delta

    if (this.gestureCooldown <= 0 && this.getRecentGestureCount() < CONFIG.Gesture.MaxPerMinute && !this.gestureLayer.isAnyGestureActive()) {
      if (Math.random() < CONFIG.Gesture.Probability) {
        const gesture = GESTURE_LIST[Math.floor(Math.random() * GESTURE_LIST.length)]
        this.gestureLayer.triggerGesture(gesture)
        this.gestureTimestamps.push(this.elapsed)
        this.gestureCooldown = randomRange(CONFIG.Gesture.CooldownMin, CONFIG.Gesture.CooldownMax)
      } else {
        this.gestureCooldown = randomRange(2, 4)
      }
    }

    if (this.timeSinceLastHeadNod > randomRange(CONFIG.Speaking.HeadNodMinInterval, CONFIG.Speaking.HeadNodMaxInterval)) {
      if (Math.random() < 0.5) {
        this.headEmphasis = [0, 0, randomRange(-CONFIG.Speaking.HeadEmphasisAmount, -CONFIG.Speaking.HeadEmphasisAmount * 0.5)]
      } else {
        this.headEmphasis = [0, 0, 0]
      }
      this.timeSinceLastHeadNod = 0
    }

    const headZ = this.currentHeadEmphasis[2]
    this.postureForward = CONFIG.Speaking.PostureForwardAmount

    this.currentHeadEmphasis[2] = damp(this.currentHeadEmphasis[2], this.headEmphasis[2], 4, context.delta)

    this.offsets = {
      head: { rotation: [0, 0, headZ] },
      spine: { rotation: [this.postureForward, 0, 0] },
      spine1: { rotation: [this.postureForward * 0.5, 0, 0] },
    }
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
