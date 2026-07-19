export type GestureTypeName =
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

export type GestureArm = 'left' | 'right' | 'both'

export type EasingType = 'linear' | 'easeIn' | 'easeOut' | 'easeInOut' | 'easeOutBack'

export interface GestureBoneTarget {
  rotation?: [number, number, number]
  position?: [number, number, number]
}

export interface GesturePhase {
  duration: number
  targets: Record<string, GestureBoneTarget>
  easing?: EasingType
}

export interface GestureDefinition {
  name: GestureTypeName
  arm: GestureArm
  phases: GesturePhase[]
  intensity?: number
}

export interface GestureRuntime {
  active: boolean
  type: GestureTypeName | null
  phaseIndex: number
  phaseTime: number
  elapsed: number
}

export interface GestureReturnState {
  active: boolean
  velocities: Map<string, [number, number, number]>
}

export interface GestureDebugFrame {
  gesture: GestureTypeName
  state: string
  progress: number
  bones: string[]
  targets: Record<string, GestureBoneTarget>
  phaseIndex: number
  elapsed: number
}
