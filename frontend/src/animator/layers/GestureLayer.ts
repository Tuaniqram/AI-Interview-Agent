import type { AnimationContext, AnimationLayer, BoneTransform, GestureType } from '../types'
import { GestureController } from '../gestures/GestureController'
import { debugGesture } from '../gestures/GestureBlender'

export const GESTURE_LAYER_CONFLICT: Record<string, { head?: true; shoulders?: true; arms?: true; spine?: true }> = {
  questionEmphasis: { head: true, arms: true },
  agreementNod: { head: true },
  shoulderEmphasis: { shoulders: true },
  smallShrug: { shoulders: true },
  chestEmphasis: { spine: true, arms: true },
  bothHandsOpen: { arms: true, shoulders: true },
  closingGesture: { arms: true, shoulders: true },
  openPalm: { arms: true },
  singleHandEmphasis: { arms: true },
  forearmLift: { arms: true },
  palmUpward: { arms: true },
  smallPointing: { arms: true },
  fingerEmphasis: { arms: true },
  handRotation: { arms: true },
  explanationGesture: { arms: true },
}

export class GestureLayer implements AnimationLayer {
  readonly name = 'GestureLayer'
  weight = 1

  private controller = new GestureController()

  constructor() {
    debugGesture('GestureLayer initialized with GestureController')
  }

  setAvailableBones(bones: string[]): void {
    this.controller.setAvailableBones(bones)
    debugGesture(`Available bones set: ${bones.join(', ')}`)
  }

  triggerGesture(type: GestureType): void {
    const started = this.controller.triggerGesture(type as any)
    if (started) {
      debugGesture(`Gesture triggered: "${type}"`)
    } else {
      console.warn(`[GestureLayer] Cannot start "${type}" — another gesture is active or unknown`)
    }
  }

  stopGesture(): void {
    this.controller.stopGesture()
    debugGesture('Gesture stopped by layer')
  }

  isAnyGestureActive(): boolean {
    return this.controller.isAnyGestureActive()
  }

  getCurrentGesture(): GestureType | null {
    return this.controller.getCurrentGesture() as GestureType | null
  }

  update(context: AnimationContext): void {
    this.controller.update(context.delta)

    if (typeof window !== 'undefined' && (window as any).DEBUG_GESTURES) {
      const debug = this.controller.getDebugFrame()
      if (debug) {
        ;(window as any).__lastGestureDebug = debug
      }
    }
  }

  getBoneOffsets(): Readonly<Record<string, BoneTransform>> {
    return this.controller.getBoneOffsets() as Record<string, BoneTransform>
  }
}
