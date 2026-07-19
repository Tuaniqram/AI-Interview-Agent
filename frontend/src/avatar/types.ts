export interface VisemeEvent {
  time: number
  value: string
  intensity: number
  duration: number
}

export interface AudioChunkEvent {
  audio: string
  sample_rate: number
  is_final: boolean
}

export interface ExpressionEvent {
  time: number
  emotion: string
  intensity: number
}

export interface GestureEvent {
  time: number
  gesture: string
  intensity: number
}

export interface WsMessage {
  session_id: string
  response_id: string
  type: string
  timestamp: number
  sequence: number
  data?: Record<string, unknown>
}

export interface LipSyncState {
  isSpeaking: boolean
  currentViseme: string | null
  nextViseme: string | null
  blendFactor: number
  audioTime: number
  morphTargets: Record<string, number>
}

export type LipSyncCallback = (targets: Record<string, number>) => void
