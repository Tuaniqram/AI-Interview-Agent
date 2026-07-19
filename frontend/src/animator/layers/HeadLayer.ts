import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { randomRange } from '../utils/Random'
import { damp, smoothstep } from '../utils/Damp'
import { getNoise } from '../utils/Noise'

interface NodEvent {
  active: boolean
  timer: number
  duration: number
  amplitude: number
}

export class HeadLayer implements AnimationLayer {
  readonly name = 'HeadLayer'
  weight = 1

  private nod: NodEvent = { active: false, timer: 0, duration: 0.6, amplitude: 0.02 }
  private currentNod = 0
  private timeToNextNod = randomRange(8, 20)
  private time = 0

  private offsets: Record<string, BoneTransform> = {}

  update(context: AnimationContext): void {
    this.time += context.delta

    this.timeToNextNod -= context.delta
    if (this.timeToNextNod <= 0 && !this.nod.active) {
      this.startNod(context)
    }

    this.updateNod(context.delta)

    const noise = getNoise()
    const microN = noise.noise2D(this.time * 0.2, 10) * 0.003
    const microT = noise.noise2D(this.time * 0.15, 20) * 0.002

    const nodZ = this.currentNod + microN

    this.offsets = {
      head: { rotation: [microT, 0, nodZ] },
    }
  }

  private startNod(context: AnimationContext): void {
    this.nod.active = true
    this.nod.timer = 0
    this.nod.duration = randomRange(0.4, 0.8)
    this.nod.amplitude = randomRange(0.01, CONFIG.Head.NodAmplitude)
    this.timeToNextNod = context.state === 'listening'
      ? randomRange(CONFIG.Listening.NodMinInterval, CONFIG.Listening.NodMaxInterval)
      : randomRange(8, 20)
  }

  private updateNod(delta: number): void {
    if (!this.nod.active) {
      this.currentNod = damp(this.currentNod, 0, 3, delta)
      return
    }

    this.nod.timer += delta
    const t = Math.min(1, this.nod.timer / this.nod.duration)

    const attack = t < 0.3 ? smoothstep(t / 0.3) : 1
    const release = t > 0.7 ? 1 - smoothstep((t - 0.7) / 0.3) : 1
    const envelope = attack * release
    this.currentNod = this.nod.amplitude * Math.sin(t * Math.PI) * envelope

    if (t >= 1) {
      this.nod.active = false
      this.currentNod = 0
    }
  }

  triggerNod(amplitude?: number, duration?: number): void {
    this.nod.active = true
    this.nod.timer = 0
    this.nod.duration = duration ?? randomRange(0.4, 0.7)
    this.nod.amplitude = amplitude ?? randomRange(0.01, 0.03)
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
