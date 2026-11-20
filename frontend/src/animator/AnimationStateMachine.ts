import type { BodyState } from './types'
import { CONFIG } from './utils/Config'
import { clamp } from './utils/Damp'

interface StateTransition {
  from: BodyState
  to: BodyState
  blendTime: number
}

const VALID_TRANSITIONS: StateTransition[] = [
  { from: 'idle', to: 'speaking', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'idle', to: 'listening', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'idle', to: 'thinking', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'speaking', to: 'idle', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'speaking', to: 'listening', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'speaking', to: 'thinking', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'listening', to: 'idle', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'listening', to: 'speaking', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'listening', to: 'thinking', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'thinking', to: 'idle', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'thinking', to: 'speaking', blendTime: CONFIG.StateTransition.BlendDuration },
  { from: 'thinking', to: 'listening', blendTime: CONFIG.StateTransition.BlendDuration },
]

export class AnimationStateMachine {
  private _currentState: BodyState = 'idle'
  private _previousState: BodyState = 'idle'
  private _transitionProgress = 1
  private _transitionTime = 0
  private _isTransitioning = false
  private _targetState: BodyState = 'idle'

  requestState(state: BodyState): void {
    if (state === this._targetState) return

    const valid = VALID_TRANSITIONS.find(
      (t) => t.from === this._currentState && t.to === state,
    )

    if (valid) {
      this._previousState = this._currentState
      this._targetState = state
      this._isTransitioning = true
      this._transitionProgress = 0
      this._transitionTime = valid.blendTime
    } else {
      this._currentState = state
      this._previousState = state
      this._targetState = state
      this._isTransitioning = false
      this._transitionProgress = 1
    }
  }

  forceState(state: BodyState): void {
    this._currentState = state
    this._previousState = state
    this._targetState = state
    this._isTransitioning = false
    this._transitionProgress = 1
  }

  update(delta: number): void {
    if (!this._isTransitioning) return

    this._transitionProgress += delta / this._transitionTime
    if (this._transitionProgress >= 1) {
      this._transitionProgress = 1
      this._currentState = this._targetState
      this._previousState = this._targetState
      this._isTransitioning = false
    }
  }

  get currentState(): BodyState {
    return this._currentState
  }

  get previousState(): BodyState {
    return this._previousState
  }

  get targetState(): BodyState {
    return this._targetState
  }

  get transitionProgress(): number {
    return clamp(this._transitionProgress, 0, 1)
  }

  get isTransitioning(): boolean {
    return this._isTransitioning
  }
}
