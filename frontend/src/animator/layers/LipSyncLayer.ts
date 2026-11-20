import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { damp } from '../utils/Damp'

export class LipSyncLayer implements AnimationLayer {
  readonly name = 'LipSyncLayer'
  weight = 1

  private jawOpen = 0
  private targetJaw = 0
  private mouthWidth = 0
  private targetMouth = 0

  private readonly JAW_VISEMES = new Set([
    'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY',
    'IH', 'IY', 'OW', 'OY', 'UH', 'UW',
    'aa', 'ae', 'ah', 'ao', 'aw', 'ay', 'eh', 'er', 'ey',
    'ih', 'iy', 'ow', 'oy', 'uh', 'uw',
    'CH', 'DD', 'FF', 'KK', 'NN', 'PP', 'RR', 'SS', 'TH',
    'ch', 'dd', 'ff', 'kk', 'nn', 'pp', 'rr', 'ss', 'th',
  ])

  update(context: AnimationContext): void {
    if (context.viseme && context.viseme !== 'sil') {
      this.targetJaw = this.JAW_VISEMES.has(context.viseme) ? 0.7 : 0.3
      this.targetMouth = context.viseme === 'FF' || context.viseme === 'SS' ? 0.4 : 0
    } else {
      this.targetJaw = 0
      this.targetMouth = 0
    }

    this.jawOpen = damp(this.jawOpen, this.targetJaw * context.audioIntensity, 30, context.delta)
    this.mouthWidth = damp(this.mouthWidth, this.targetMouth * context.audioIntensity, 20, context.delta)
  }

  getJawOpenValue(): number {
    return this.jawOpen
  }

  getMorphTargets(): Record<string, number> {
    const targets: Record<string, number> = {}
    targets[CONFIG.LipSync.JawOpenMorph] = this.jawOpen
    return targets
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return {}
  }
}
