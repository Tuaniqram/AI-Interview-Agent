import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { getNoise } from '../utils/Noise'

export class BreathingLayer implements AnimationLayer {
  readonly name = 'BreathingLayer'
  weight = 1
  private time = 0
  private offsets: Record<string, BoneTransform> = {}

  update(context: AnimationContext): void {
    this.time += context.delta
    this.offsets = {}

    const cycle = CONFIG.Breathing.CycleTime
    const t = this.time / cycle
    const noise = getNoise()
    const n = noise.noise2D(t * 0.5, 0) * 0.3
    const breath = Math.sin(t * Math.PI * 2) * 0.5 + 0.5
    const amplitude = breath + n * 0.1

    const spineRx = amplitude * CONFIG.Breathing.SpineAmplitude
    const spine1Rx = amplitude * CONFIG.Breathing.UpperSpineAmplitude
    const spine2Rx = amplitude * CONFIG.Breathing.UpperSpineAmplitude * 0.5
    const shoulderRy = amplitude * CONFIG.Breathing.ShoulderAmplitude

    this.offsets.spine = { rotation: [spineRx, 0, 0] }
    this.offsets.spine1 = { rotation: [spine1Rx, 0, 0] }
    this.offsets.spine2 = { rotation: [spine2Rx, 0, 0] }
    this.offsets.leftShoulder = { rotation: [0, 0, shoulderRy] }
    this.offsets.rightShoulder = { rotation: [0, 0, -shoulderRy] }
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
