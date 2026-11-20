import type { Bone } from 'three'
import type { BoneMap, AnimationContext, BodyState, BoneTransform } from './types'
import { AnimationScheduler } from './AnimationScheduler'
import { AnimationStateMachine } from './AnimationStateMachine'
import { BreathingLayer } from './layers/BreathingLayer'
import { PostureLayer } from './layers/PostureLayer'
import { IdleLayer } from './layers/IdleLayer'
import { WeightShiftLayer } from './layers/WeightShiftLayer'
import { MicroMovementLayer } from './layers/MicroMovementLayer'
import { EyeLayer } from './layers/EyeLayer'
import { BlinkLayer } from './layers/BlinkLayer'
import { HeadLayer } from './layers/HeadLayer'
import { LipSyncLayer } from './layers/LipSyncLayer'
import { GestureLayer, GESTURE_LAYER_CONFLICT } from './layers/GestureLayer'
import { SpeakingLayer } from './layers/SpeakingLayer'
import { ListeningLayer } from './layers/ListeningLayer'
import { ThinkingLayer } from './layers/ThinkingLayer'
import { storeRestPose, getBoneNames, getGestureRelevantBones } from './utils/BoneUtils'
import { damp, clamp } from './utils/Damp'

export class BodyAnimator {
  readonly scheduler: AnimationScheduler
  readonly stateMachine: AnimationStateMachine
  readonly gestureLayer: GestureLayer
  readonly speakingLayer: SpeakingLayer
  readonly listeningLayer: ListeningLayer
  readonly thinkingLayer: ThinkingLayer
  readonly headLayer: HeadLayer
  readonly blinkLayer: BlinkLayer
  readonly lipSyncLayer: LipSyncLayer
  readonly eyeLayer: EyeLayer

  private readonly boneMap: BoneMap
  private readonly restPose: Map<string, { position: [number, number, number]; rotation: [number, number, number] }>
  private readonly boneNames: ReturnType<typeof getBoneNames>

  private readonly breathing: BreathingLayer
  private readonly posture: PostureLayer
  private readonly idle: IdleLayer
  private readonly weightShift: WeightShiftLayer
  private readonly micro: MicroMovementLayer

  private elapsed = 0
  private audioIntensity = 0.5
  private viseme: string | null = null

  private accumulated: Record<string, { pos: [number, number, number]; rot: [number, number, number] }> = {}

  constructor(boneMap: BoneMap) {
    this.boneMap = boneMap
    this.boneNames = getBoneNames()
    this.restPose = storeRestPose(boneMap)

    this.applyArmRestCorrection()

    this.scheduler = new AnimationScheduler()
    this.stateMachine = new AnimationStateMachine()
    this.gestureLayer = new GestureLayer()
    this.gestureLayer.setAvailableBones(getGestureRelevantBones())
    this.speakingLayer = new SpeakingLayer(this.gestureLayer)
    this.listeningLayer = new ListeningLayer()
    this.thinkingLayer = new ThinkingLayer()
    this.headLayer = new HeadLayer()
    this.blinkLayer = new BlinkLayer()
    this.lipSyncLayer = new LipSyncLayer()
    this.eyeLayer = new EyeLayer()

    this.breathing = new BreathingLayer()
    this.posture = new PostureLayer()
    this.idle = new IdleLayer()
    this.weightShift = new WeightShiftLayer()
    this.micro = new MicroMovementLayer()

    this.initAccumulator()
  }

  private applyArmRestCorrection(): void {
    const armCorrection: Record<string, [number, number, number]> = {
      leftArm: [1.2, 0, 0],
      rightArm: [1.2, 0, 0],
      leftForeArm: [0.2, 0, 0],
      rightForeArm: [0.2, 0, 0],
    }
    for (const [name, offset] of Object.entries(armCorrection)) {
      const rest = this.restPose.get(name)
      if (rest) {
        rest.rotation[0] += offset[0]
        rest.rotation[1] += offset[1]
        rest.rotation[2] += offset[2]
      } else {
        console.warn(`[BodyAnimator] Arm bone "${name}" not found — arm will stay at GLB default pose`)
      }
    }
  }

  private initAccumulator(): void {
    for (const name of this.boneNames) {
      this.accumulated[name] = { pos: [0, 0, 0], rot: [0, 0, 0] }
    }
  }

  setState(state: BodyState): void {
    this.stateMachine.requestState(state)
  }

  setViseme(viseme: string | null, intensity = 0.5): void {
    this.viseme = viseme
    this.audioIntensity = intensity
  }

  setAudioIntensity(intensity: number): void {
    this.audioIntensity = clamp(intensity, 0, 1)
  }

  update(delta: number): void {
    if (delta > 0.1) delta = 0.1

    this.elapsed += delta
    this.stateMachine.update(delta)
    this.scheduler.update(delta)

    const ctx: AnimationContext = {
      state: this.stateMachine.currentState,
      elapsed: this.elapsed,
      delta,
      viseme: this.viseme,
      audioIntensity: this.audioIntensity,
      transitionProgress: this.stateMachine.transitionProgress,
    }

    const transP = ctx.transitionProgress
    const isTransitioning = this.stateMachine.isTransitioning

    this.breathing.weight = 1
    this.posture.weight = 1
    this.micro.weight = 1
    this.weightShift.weight = 1
    this.eyeLayer.weight = 1
    this.blinkLayer.weight = 1
    this.headLayer.weight = 1
    this.gestureLayer.weight = 1
    this.lipSyncLayer.weight = 1

    this.idle.weight = ctx.state === 'idle' ? (isTransitioning ? transP : 1) : (isTransitioning ? 1 - transP : 0)
    this.speakingLayer.weight = ctx.state === 'speaking' ? (isTransitioning ? transP : 1) : (isTransitioning ? 1 - transP : 0)
    this.listeningLayer.weight = ctx.state === 'listening' ? (isTransitioning ? transP : 1) : (isTransitioning ? 1 - transP : 0)
    this.thinkingLayer.weight = ctx.state === 'thinking' ? (isTransitioning ? transP : 1) : (isTransitioning ? 1 - transP : 0)

    const gestureActive = this.gestureLayer.isAnyGestureActive()
    if (gestureActive) {
      const g = GESTURE_LAYER_CONFLICT[this.gestureLayer.getCurrentGesture() ?? '']
      if (g) {
        if (g.head) { this.headLayer.weight *= 0.2; this.idle.weight *= 0.2 }
        if (g.shoulders) { this.breathing.weight *= 0.5; this.posture.weight *= 0.3; this.weightShift.weight *= 0.3; this.micro.weight *= 0.5 }
        if (g.spine) { this.speakingLayer.weight *= 0.5; this.listeningLayer.weight *= 0.5; this.thinkingLayer.weight *= 0.5 }
        if (g.arms) { this.weightShift.weight *= 0.5; this.posture.weight *= 0.5 }
      } else {
        this.headLayer.weight *= 0.5
      }
    }

    this.breathing.update(ctx)
    this.posture.update(ctx)
    this.idle.update(ctx)
    this.weightShift.update(ctx)
    this.micro.update(ctx)
    this.eyeLayer.update(ctx)
    this.blinkLayer.update(ctx)
    this.headLayer.update(ctx)
    this.speakingLayer.update(ctx)
    this.listeningLayer.update(ctx)
    this.thinkingLayer.update(ctx)
    this.gestureLayer.update(ctx)
    this.lipSyncLayer.update(ctx)

    this.accumulateLayer(this.breathing)
    this.accumulateLayer(this.posture)
    this.accumulateLayer(this.idle)
    this.accumulateLayer(this.weightShift)
    this.accumulateLayer(this.micro)
    this.accumulateLayer(this.eyeLayer)
    this.accumulateLayer(this.headLayer)
    this.accumulateLayer(this.speakingLayer)
    this.accumulateLayer(this.listeningLayer)
    this.accumulateLayer(this.thinkingLayer)
    this.accumulateLayer(this.gestureLayer)

    this.applyToBones(delta)
  }

  private accumulateLayer(layer: { weight: number; getBoneOffsets(): Readonly<Record<string, BoneTransform>> }): void {
    const w = layer.weight
    if (w <= 0.001) return

    const offsets = layer.getBoneOffsets()
    for (const [boneName, transform] of Object.entries(offsets)) {
      if (!this.accumulated[boneName]) continue
      const acc = this.accumulated[boneName]
      if (transform.rotation) {
        acc.rot[0] += transform.rotation[0] * w
        acc.rot[1] += transform.rotation[1] * w
        acc.rot[2] += transform.rotation[2] * w
      }
      if (transform.position) {
        acc.pos[0] += transform.position[0] * w
        acc.pos[1] += transform.position[1] * w
        acc.pos[2] += transform.position[2] * w
      }
    }
  }

  private applyToBones(delta: number): void {
    for (const name of this.boneNames) {
      const bone = this.boneMap[name] as Bone | undefined
      if (!bone) continue

      const rest = this.restPose.get(name)
      if (!rest) continue

      const acc = this.accumulated[name]

      const targetRx = rest.rotation[0] + acc.rot[0]
      const targetRy = rest.rotation[1] + acc.rot[1]
      const targetRz = rest.rotation[2] + acc.rot[2]
      const targetPx = rest.position[0] + acc.pos[0]
      const targetPy = rest.position[1] + acc.pos[1]
      const targetPz = rest.position[2] + acc.pos[2]

      bone.rotation.x = damp(bone.rotation.x, targetRx, 8, delta)
      bone.rotation.y = damp(bone.rotation.y, targetRy, 8, delta)
      bone.rotation.z = damp(bone.rotation.z, targetRz, 8, delta)

      bone.position.x = damp(bone.position.x, targetPx, 8, delta)
      bone.position.y = damp(bone.position.y, targetPy, 8, delta)
      bone.position.z = damp(bone.position.z, targetPz, 8, delta)

      acc.rot[0] = 0
      acc.rot[1] = 0
      acc.rot[2] = 0
      acc.pos[0] = 0
      acc.pos[1] = 0
      acc.pos[2] = 0
    }
  }

  getBlinkInfluence(): number {
    return this.blinkLayer.getBlinkInfluence()
  }

  getMorphTargets(): Record<string, number> {
    return this.lipSyncLayer.getMorphTargets()
  }
}
