import type { VisemeEvent } from './types'
import { clamp } from '../animator/utils/Damp'

const VISEME_TO_MORPHS: Record<string, Record<string, number>> = {
  AA: { jawOpen: 0.65, mouthOpen: 0.55, aa: 0.85 },
  AE: { jawOpen: 0.6, aa: 0.8 },
  AH: { jawOpen: 0.55, aa: 0.7 },
  AO: { jawOpen: 0.45, mouthFunnel: 0.35, oh: 0.7 },
  AW: { aa: 0.6, oh: 0.45 },
  AY: { aa: 0.7, ih: 0.35 },
  B: { mouthClose: 0.6, PP: 0.8 },
  CH: { CH: 0.85 },
  D: { DD: 0.85, jawOpen: 0.25 },
  DH: { TH: 0.85 },
  EH: { E: 0.85, jawOpen: 0.35 },
  ER: { RR: 0.7, jawOpen: 0.25 },
  EY: { E: 0.8, ih: 0.25 },
  F: { FF: 0.85 },
  G: { kk: 0.7, jawOpen: 0.25 },
  HH: { aa: 0.25 },
  IH: { ih: 0.85, jawOpen: 0.15 },
  IY: { ih: 0.8, E: 0.25 },
  JH: { CH: 0.7, DD: 0.25 },
  K: { kk: 0.85, jawOpen: 0.25 },
  L: { nn: 0.55, jawOpen: 0.15 },
  M: { nn: 0.7, mouthClose: 0.25 },
  N: { nn: 0.85 },
  NG: { kk: 0.6, jawOpen: 0.15 },
  OW: { oh: 0.85, mouthFunnel: 0.55 },
  OY: { oh: 0.6, ih: 0.35 },
  P: { PP: 0.85, mouthClose: 0.7 },
  R: { RR: 0.85, mouthPucker: 0.15 },
  S: { SS: 0.85 },
  SH: { CH: 0.7, SH: 0.25 },
  SIL: { sil: 0.85 },
  T: { DD: 0.8, jawOpen: 0.15 },
  TH: { TH: 0.85 },
  UH: { oh: 0.55, mouthFunnel: 0.35 },
  UW: { oh: 0.7, mouthFunnel: 0.35 },
  V: { FF: 0.8 },
  W: { oh: 0.6, mouthFunnel: 0.35 },
  Y: { ih: 0.45, E: 0.25 },
  Z: { SS: 0.7 },
  ZH: { CH: 0.6, SH: 0.25 },

  DD: { DD: 0.85, jawOpen: 0.25 },
  FF: { FF: 0.85 },
  KK: { kk: 0.85, jawOpen: 0.25 },
  NN: { nn: 0.85 },
  PP: { PP: 0.85, mouthClose: 0.7 },
  RR: { RR: 0.85, mouthPucker: 0.15 },
  SS: { SS: 0.85 },
  aa: { aa: 0.85, jawOpen: 0.6 },
  ih: { ih: 0.85, jawOpen: 0.15 },
  kk: { kk: 0.85, jawOpen: 0.25 },
  nn: { nn: 0.8 },
  oh: { oh: 0.85, mouthFunnel: 0.45 },
  ou: { oh: 0.8, mouthFunnel: 0.35 },
  E: { E: 0.85, jawOpen: 0.35 },
  sil: {},
}

const BLEND_DURATION = 0.05

const PER_MORPH_SMOOTH: Record<string, number> = {
  jawOpen: 0.6,
  mouthOpen: 0.6,
  mouthClose: 0.6,
  mouthFunnel: 0.6,
  mouthPucker: 0.6,
  aa: 0.5,
  oh: 0.5,
  ih: 0.5,
  kk: 0.7,
  nn: 0.6,
  DD: 0.7,
  FF: 0.8,
  PP: 0.7,
  RR: 0.6,
  SS: 0.8,
  TH: 0.7,
  CH: 0.7,
  SH: 0.6,
  E: 0.5,
  sil: 0.4,
}

export class VisemeEngine {
  private queue: VisemeEvent[] = []
  private currentViseme: VisemeEvent | null = null
  private fadeValue = 0
  private prevMorphValues: Record<string, number> = {}
  private silenceStartTime = -1
  private silenceDuration = 0

  get current(): string | null {
    return this.currentViseme?.value ?? null
  }

  get next(): string | null {
    return this.queue[0]?.value ?? null
  }

  get blendFactor(): number {
    return this.fadeValue
  }

  loadVisemes(visemes: VisemeEvent[]): void {
    this.queue = [...visemes].sort((a, b) => a.time - b.time)
    this.currentViseme = null
    this.fadeValue = 0
    this.silenceStartTime = -1
  }

  appendViseme(viseme: VisemeEvent): void {
    const idx = this.queue.findIndex((v) => v.time > viseme.time)
    if (idx < 0) {
      this.queue.push(viseme)
    } else {
      this.queue.splice(idx, 0, viseme)
    }
  }

  setSilence(duration: number, elapsed: number = 0): void {
    this.queue = []
    this.currentViseme = null
    this.fadeValue = 0
    this.silenceStartTime = elapsed
    this.silenceDuration = duration
  }

  update(elapsed: number): Record<string, number> {
    if (this.silenceStartTime >= 0) {
      const dt = elapsed - this.silenceStartTime
      const t = dt / this.silenceDuration
      if (t >= 1) {
        this.silenceStartTime = -1
        this.prevMorphValues = {}
        return {}
      }
      const fade = 1 - t
      const result: Record<string, number> = {}
      for (const [key, val] of Object.entries(this.prevMorphValues)) {
        result[key] = val * fade
      }
      return result
    }

    while (this.queue.length > 0 && this.queue[0].time <= elapsed) {
      this.currentViseme = this.queue.shift()!
      this.fadeValue = 0
    }

    if (!this.currentViseme) {
      return {}
    }

    const nextViseme = this.queue[0]
    const visemeEnd = this.currentViseme.time + this.currentViseme.duration

    if (elapsed < visemeEnd) {
      this.fadeValue = Math.min(1, this.fadeValue + 0.05 / BLEND_DURATION)
    } else if (nextViseme) {
      this.fadeValue = Math.max(0, this.fadeValue - 0.05 / BLEND_DURATION)
    } else {
      this.fadeValue = Math.max(0, this.fadeValue - 0.05 / BLEND_DURATION)
      if (this.fadeValue <= 0) {
        this.currentViseme = null
        return {}
      }
    }

    const currentMorphs = this.getVisemeMorphs(this.currentViseme)
    const fade = this.fadeValue * this.currentViseme.intensity

    if (!nextViseme) {
      const result = this.applyWeight(currentMorphs, fade)
      for (const key of Object.keys(result)) {
        const smooth = PER_MORPH_SMOOTH[key]
        if (smooth !== undefined) {
          const prev = this.prevMorphValues[key] ?? 0
          const smoothed = prev + (result[key] - prev) * smooth
          result[key] = smoothed
          this.prevMorphValues[key] = smoothed
        } else {
          this.prevMorphValues[key] = result[key]
        }
      }
      this.cleanPrevMorphValues()
      return result
    }

    const nextTime = nextViseme.time
    const elapsedSinceCurrent = elapsed - this.currentViseme.time
    const transition = nextTime - this.currentViseme.time
    const blendWeight = transition > 0 ? clamp(elapsedSinceCurrent / transition, 0, 1) : 1
    const smoothBlend = blendWeight * blendWeight * (3 - 2 * blendWeight)

    const nextMorphs = this.getVisemeMorphs(nextViseme)
    const blended: Record<string, number> = {}

    const allKeys = new Set([
      ...Object.keys(currentMorphs),
      ...Object.keys(nextMorphs),
    ])

    for (const key of allKeys) {
      const cv = currentMorphs[key] ?? 0
      const nv = nextMorphs[key] ?? 0
      let value = (cv * (1 - smoothBlend) + nv * smoothBlend) * fade

      const smooth = PER_MORPH_SMOOTH[key]
      if (smooth !== undefined) {
        const prev = this.prevMorphValues[key] ?? 0
        value = prev + (value - prev) * smooth
        this.prevMorphValues[key] = value
      } else {
        this.prevMorphValues[key] = value
      }

      blended[key] = value
    }

    this.cleanPrevMorphValues()
    return blended
  }

  private cleanPrevMorphValues(): void {
    for (const key of Object.keys(this.prevMorphValues)) {
      if (this.prevMorphValues[key] === 0) {
        delete this.prevMorphValues[key]
      }
    }
  }

  private getVisemeMorphs(viseme: VisemeEvent): Record<string, number> {
    return VISEME_TO_MORPHS[viseme.value] ?? {}
  }

  private applyWeight(
    morphs: Record<string, number>,
    weight: number,
  ): Record<string, number> {
    const result: Record<string, number> = {}
    for (const [key, val] of Object.entries(morphs)) {
      result[key] = val * weight
    }
    return result
  }

  clear(): void {
    this.queue = []
    this.currentViseme = null
    this.fadeValue = 0
    this.prevMorphValues = {}
    this.silenceStartTime = -1
  }
}
