import { getCandidateToken } from '../utils/candidateToken'
import type { Mesh } from 'three'
import type { VisemeEvent, ExpressionEvent, GestureEvent, WsMessage, LipSyncState } from './types'
import type { GestureType } from '../animator/types'
import type { AvatarEmotion } from '../types/avatar'
import { VisemeEngine } from './VisemeEngine'
import { AudioSync } from './AudioSync'
import { MorphTargetController } from './MorphTargetController'
import { ExpressionController } from './ExpressionController'
import { BodyAnimator } from '../animator/BodyAnimator'
import { mapGestureHint } from './gestureMapper'

export class LipSyncController {
  readonly visemeEngine: VisemeEngine
  readonly audioSync: AudioSync
  readonly morphTargetController: MorphTargetController
  readonly expressionController: ExpressionController

  private ws: WebSocket | null = null
  private bodyAnimator: BodyAnimator | null = null
  private _isSpeaking = false
  private _speechActive = false
  private _speakingSince = 0
  private expressionQueue: ExpressionEvent[] = []
  private gestureQueue: GestureEvent[] = []
  private onLipSyncUpdate: ((targets: Record<string, number>) => void) | null = null
  private _onConnected: (() => void) | null = null
  private _lastSessionId = ''
  private _lastBaseUrl?: string
  private _queuedSpeak: { text: string; emotion: string } | null = null
  private slot: Record<string, number> = {}

  constructor() {
    this.visemeEngine = new VisemeEngine()
    this.audioSync = new AudioSync()
    this.morphTargetController = new MorphTargetController()
    this.expressionController = new ExpressionController()
  }

  get isSpeaking(): boolean {
    return this._isSpeaking
  }

  setMeshes(meshes: Mesh[]): void {
    this.morphTargetController.setMeshes(meshes)
  }

  setBodyAnimator(animator: BodyAnimator): void {
    this.bodyAnimator = animator
  }

  setOnLipSyncUpdate(callback: (targets: Record<string, number>) => void): void {
    this.onLipSyncUpdate = callback
  }

  triggerGesture(type: GestureType): void {
    this.bodyAnimator?.gestureLayer.triggerGesture(type)
  }

  stopGesture(): void {
    this.bodyAnimator?.gestureLayer.stopGesture()
  }

  hasActiveGesture(): boolean {
    return this.bodyAnimator?.gestureLayer.isAnyGestureActive() ?? false
  }

  setExpression(emotion: AvatarEmotion, intensity = 1): void {
    this.expressionController.setEmotion(emotion, intensity)
  }

  set onConnected(callback: (() => void) | null) {
    this._onConnected = callback
  }

  connect(sessionId: string, baseUrl?: string): void {
    this.disconnect()

    this._lastSessionId = sessionId
    this._lastBaseUrl = baseUrl

    const host = baseUrl ?? window.location.host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const token = getCandidateToken()
    const url = token
      ? `${protocol}//${host}/ws/avatar/${sessionId}?token=${token}`
      : `${protocol}//${host}/ws/avatar/${sessionId}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('[LipSync] WebSocket connected')
      this._onConnected?.()
      if (this._queuedSpeak) {
        const q = this._queuedSpeak
        this._queuedSpeak = null
        this._sendSpeak(q.text, q.emotion)
      }
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        this.handleMessage(msg)
      } catch (err) {
        console.error('[LipSync] Parse error:', err)
      }
    }

    this.ws.onclose = () => {
      console.log('[LipSync] WebSocket closed')
      this._isSpeaking = false
    }

    this.ws.onerror = (err) => {
      console.error('[LipSync] WebSocket error:', err)
    }
  }

  disconnect(): void {
    this.ws?.close()
    this.ws = null
    this.visemeEngine.clear()
    this.audioSync.stop()
    this.expressionQueue = []
    this.gestureQueue = []
    this._isSpeaking = false
    this._speechActive = false
    this._speakingSince = 0
  }

  speak(text: string, emotion = 'neutral'): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[LipSync] WebSocket not open, reconnecting...')
      this._queuedSpeak = { text, emotion }
      if (this._lastSessionId) {
        this.connect(this._lastSessionId, this._lastBaseUrl)
      }
      return
    }

    this._sendSpeak(text, emotion)
  }

  private _sendSpeak(text: string, emotion: string): void {
    this.audioSync.stop()
    this.expressionQueue = []
    this.gestureQueue = []

    this.ws!.send(JSON.stringify({
      type: 'speak',
      text,
      emotion,
    }))
  }

  update(delta: number): LipSyncState {
    const audioTime = this.audioSync.currentTime
    const elapsed = audioTime

    const visemeMorphs = this.visemeEngine.update(elapsed)
    const expressionMorphs = this.expressionController.update(delta, this._isSpeaking)

    const merged = this.morphTargetController.mergeTargets(
      visemeMorphs,
      expressionMorphs,
      0.6,
    )

    this.slot = merged
    this.onLipSyncUpdate?.(merged)

    this.checkExpressions(elapsed)
    this.checkGestures(elapsed)

    // End speech when: speech_end received + audio finished + viseme fade complete
    if (this._isSpeaking) {
      const hasWork = this._speechActive || this.visemeEngine.isActive || this.audioSync.isPlaying
      if (!hasWork) {
        this._isSpeaking = false
        this._speakingSince = 0
      }

      // Safety: speech_end received but audio never started → force end after 5s real time
      if (!this._speechActive && !this.audioSync.isPlaying && this._speakingSince > 0 && Date.now() - this._speakingSince > 5000) {
        console.log('[LipSync] force end (audio timeout):', { elapsedMs: Date.now() - this._speakingSince })
        this._isSpeaking = false
        this._speakingSince = 0
      }
    }

    return {
      isSpeaking: this._isSpeaking,
      currentViseme: this.visemeEngine.current,
      nextViseme: this.visemeEngine.next,
      blendFactor: this.visemeEngine.blendFactor,
      audioTime,
      morphTargets: merged,
    }
  }

  getMorphTargets(): Record<string, number> {
    return this.slot
  }

  private handleMessage(msg: WsMessage): void {
    const data = msg.data ?? {}

    switch (msg.type) {
      case 'session_ready':
        console.log('[LipSync] Session ready:', data)
        this.audioSync.ensureResumed()
        break

      case 'speech_start':
        this._isSpeaking = true
        this._speechActive = true
        this._speakingSince = Date.now()
        this.visemeEngine.clear()
        break

      case 'audio_chunk':
        this.handleAudioChunk(data as Record<string, unknown>)
        break

      case 'viseme':
        this.handleViseme(data as Record<string, unknown>)
        break

      case 'expression':
        this.handleExpression(data as Record<string, unknown>)
        break

      case 'gesture':
        this.handleGesture(data as Record<string, unknown>)
        break

      case 'speech_end':
        this._speechActive = false
        break

      case 'error':
        console.error('[LipSync] Server error:', data)
        break
    }
  }

  private handleAudioChunk(data: Record<string, unknown>): void {
    const audioData = data['audio'] as string
    const isFinal = data['is_final'] as boolean

    if (audioData) {
      this.audioSync.appendChunk(audioData)
    }

    if (isFinal) {
      this.audioSync.play()
    }
  }

  private handleViseme(data: Record<string, unknown>): void {
    const viseme: VisemeEvent = {
      time: data['time'] as number,
      value: data['value'] as string,
      intensity: (data['intensity'] as number) ?? 0.8,
      duration: (data['duration'] as number) ?? 0.1,
    }
    this.visemeEngine.appendViseme(viseme)
  }

  private handleExpression(data: Record<string, unknown>): void {
    this.expressionQueue.push({
      time: data['time'] as number,
      emotion: data['emotion'] as string,
      intensity: (data['intensity'] as number) ?? 0.5,
    })
  }

  private handleGesture(data: Record<string, unknown>): void {
    const hint = mapGestureHint(data['gesture'] as string)
    if (!hint) return
    this.gestureQueue.push({
      time: data['time'] as number,
      gesture: hint,
      intensity: (data['intensity'] as number) ?? 0.5,
    })
  }

  private checkExpressions(elapsed: number): void {
    while (this.expressionQueue.length > 0 && this.expressionQueue[0].time <= elapsed) {
      const expr = this.expressionQueue.shift()!
      this.expressionController.setEmotion(
        expr.emotion as AvatarEmotion,
        expr.intensity,
      )
    }
  }

  private checkGestures(elapsed: number): void {
    while (this.gestureQueue.length > 0 && this.gestureQueue[0].time <= elapsed) {
      const gest = this.gestureQueue.shift()!
      this.bodyAnimator?.gestureLayer.triggerGesture(gest.gesture as any)
    }
  }

  async testLocal(visemes: VisemeEvent[], duration: number): Promise<void> {
    this.audioSync.stop()
    this.visemeEngine.loadVisemes(visemes)
    this._isSpeaking = true
    this.expressionQueue = []
    this.gestureQueue = []

    await this.audioSync.init()
    const ctx = (this.audioSync as any).audioContext as AudioContext
    if (!ctx) return

    const sampleRate = ctx.sampleRate
    const length = Math.floor(sampleRate * duration)
    const buffer = ctx.createBuffer(1, length, sampleRate)
    buffer.getChannelData(0).fill(0)

    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    source.start()

    ;(this.audioSync as any)._isPlaying = true
    ;(this.audioSync as any).startTime = ctx.currentTime
    ;(this.audioSync as any).pausedAt = 0

    source.onended = () => {
      this._isSpeaking = false
      setTimeout(() => this.visemeEngine.setSilence(0.15, this.audioSync.currentTime), 50)
    }
  }

  destroy(): void {
    this.disconnect()
    this.audioSync.destroy()
  }
}
