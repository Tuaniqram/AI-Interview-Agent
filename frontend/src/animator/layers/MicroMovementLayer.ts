import type { AnimationContext, AnimationLayer } from '../types'
import type { BoneTransform } from '../types'
import { CONFIG } from '../utils/Config'
import { randomRange } from '../utils/Random'
import { damp } from '../utils/Damp'

interface MicroAdjustment {
  bone: string
  target: [number, number, number]
  current: [number, number, number]
  active: boolean
  time: number
  duration: number
}

export class MicroMovementLayer implements AnimationLayer {
  readonly name = 'MicroMovementLayer'
  weight = 1

  private adjustments: MicroAdjustment[] = [
    { bone: 'neck', target: [0, 0, 0], current: [0, 0, 0], active: false, time: 0, duration: 2 },
    { bone: 'leftShoulder', target: [0, 0, 0], current: [0, 0, 0], active: false, time: 0, duration: 2 },
    { bone: 'spine1', target: [0, 0, 0], current: [0, 0, 0], active: false, time: 0, duration: 2 },
  ]

  private cooldowns: number[] = [
    randomRange(CONFIG.Micro.AdjustmentIntervalMin, CONFIG.Micro.AdjustmentIntervalMax),
    randomRange(CONFIG.Micro.AdjustmentIntervalMin, CONFIG.Micro.AdjustmentIntervalMax),
    randomRange(CONFIG.Micro.AdjustmentIntervalMin, CONFIG.Micro.AdjustmentIntervalMax),
  ]

  private offsets: Record<string, BoneTransform> = {}

  update(context: AnimationContext): void {
    for (let i = 0; i < this.adjustments.length; i++) {
      const adj = this.adjustments[i]

      if (!adj.active) {
        this.cooldowns[i] -= context.delta
        if (this.cooldowns[i] <= 0) {
          this.startAdjustment(adj, i)
        }
      }

      if (adj.active) {
        adj.time += context.delta
        const progress = Math.min(1, adj.time / adj.duration)

        adj.current[0] = damp(adj.current[0], adj.target[0], 3, context.delta)
        adj.current[1] = damp(adj.current[1], adj.target[1], 3, context.delta)
        adj.current[2] = damp(adj.current[2], adj.target[2], 3, context.delta)

        if (progress >= 1) {
          adj.active = false
          this.cooldowns[i] = randomRange(
            CONFIG.Micro.AdjustmentIntervalMin,
            CONFIG.Micro.AdjustmentIntervalMax,
          )
        }
      }
    }

    this.offsets = {
      neck: { rotation: [this.adjustments[0].current[0], this.adjustments[0].current[1], this.adjustments[0].current[2]] },
      leftShoulder: { rotation: [this.adjustments[1].current[0], this.adjustments[1].current[1], this.adjustments[1].current[2]] },
      spine1: { rotation: [this.adjustments[2].current[0], this.adjustments[2].current[1], this.adjustments[2].current[2]] },
    }
  }

  private startAdjustment(adj: MicroAdjustment, _index: number): void {
    adj.active = true
    adj.time = 0
    adj.duration = randomRange(1.5, 3.5)

    switch (adj.bone) {
      case 'neck':
        adj.target = [
          randomRange(-CONFIG.Micro.NeckAdjustAmount, CONFIG.Micro.NeckAdjustAmount),
          randomRange(-CONFIG.Micro.NeckAdjustAmount * 0.5, CONFIG.Micro.NeckAdjustAmount * 0.5),
          0,
        ]
        break
      case 'leftShoulder':
        adj.target = [
          randomRange(-CONFIG.Micro.ShoulderRelaxAmount, 0),
          0,
          randomRange(-CONFIG.Micro.ShoulderRelaxAmount, CONFIG.Micro.ShoulderRelaxAmount),
        ]
        break
      case 'spine1':
        adj.target = [
          randomRange(-CONFIG.Micro.TorsoCorrectionAmount, CONFIG.Micro.TorsoCorrectionAmount),
          0,
          randomRange(-CONFIG.Micro.TorsoCorrectionAmount, CONFIG.Micro.TorsoCorrectionAmount),
        ]
        break
    }
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.offsets
  }
}
