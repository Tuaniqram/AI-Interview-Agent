import type { Bone } from 'three'

export type BodyState = 'idle' | 'speaking' | 'listening' | 'thinking'

export type GestureType =
  | 'openPalm'
  | 'singleHandEmphasis'
  | 'bothHandsOpen'
  | 'forearmLift'
  | 'palmUpward'
  | 'smallPointing'
  | 'shoulderEmphasis'
  | 'chestEmphasis'
  | 'fingerEmphasis'
  | 'handRotation'
  | 'smallShrug'
  | 'questionEmphasis'
  | 'agreementNod'
  | 'explanationGesture'
  | 'closingGesture'

export type BlinkType = 'single' | 'double' | 'slow'

export interface BoneTransform {
  position?: [number, number, number]
  rotation?: [number, number, number]
}

export interface AnimationContext {
  state: BodyState
  elapsed: number
  delta: number
  viseme: string | null
  audioIntensity: number
  transitionProgress: number
}

export interface AnimationLayer {
  readonly name: string
  weight: number
  update(context: AnimationContext): void
  getBoneOffsets(): Readonly<Record<string, BoneTransform>>
}

export interface GesturePhase {
  duration: number
  targets: Record<string, BoneTransform>
}

export interface GestureDefinition {
  name: GestureType
  arm: 'left' | 'right' | 'both'
  phases: GesturePhase[]
}

export interface GestureState {
  active: boolean
  type: GestureType | null
  phaseIndex: number
  phaseTime: number
  totalTime: number
  elapsed: number
}

export interface ScheduledTimer {
  id: number
  remaining: number
  callback: () => void
  repeat: boolean
  repeatInterval: number
}

export interface SaccadeTarget {
  x: number
  y: number
  holdTime: number
}

export interface LayerBoneOffsets {
  spine?: BoneTransform
  spine1?: BoneTransform
  spine2?: BoneTransform
  head?: BoneTransform
  neck?: BoneTransform
  leftEye?: BoneTransform
  rightEye?: BoneTransform
  leftArm?: BoneTransform
  rightArm?: BoneTransform
  leftForeArm?: BoneTransform
  rightForeArm?: BoneTransform
  leftShoulder?: BoneTransform
  rightShoulder?: BoneTransform
  leftHand?: BoneTransform
  rightHand?: BoneTransform
}

export type BoneName = keyof LayerBoneOffsets

export interface BoneMap {
  spine?: Bone
  spine1?: Bone
  spine2?: Bone
  head?: Bone
  neck?: Bone
  leftEye?: Bone
  rightEye?: Bone
  leftArm?: Bone
  rightArm?: Bone
  leftForeArm?: Bone
  rightForeArm?: Bone
  leftShoulder?: Bone
  rightShoulder?: Bone
  leftHand?: Bone
  rightHand?: Bone
}
