export class AudioSync {
  private audioContext: AudioContext | null = null
  private source: AudioBufferSourceNode | null = null
  private gainNode: GainNode | null = null
  private startTime = 0
  private pausedAt = 0
  private _isPlaying = false
  private bufferQueue: AudioBuffer[] = []
  private totalDuration = 0
  private chunks: Uint8Array[] = []

  get isPlaying(): boolean {
    return this._isPlaying
  }

  get currentTime(): number {
    if (!this._isPlaying || !this.audioContext) return this.pausedAt
    return this.audioContext.currentTime - this.startTime + this.pausedAt
  }

  get duration(): number {
    return this.totalDuration
  }

  async init(): Promise<void> {
    if (this.audioContext) return
    this.audioContext = new AudioContext()
    this.gainNode = this.audioContext.createGain()
    this.gainNode.gain.value = 1
    this.gainNode.connect(this.audioContext.destination)
  }

  appendChunk(base64Data: string): void {
    const binary = atob(base64Data)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i)
    }
    this.chunks.push(bytes)
  }

  async play(): Promise<void> {
    if (!this.audioContext || this._isPlaying) return
    if (this.chunks.length === 0) return

    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume()
    }

    const totalLength = this.chunks.reduce((sum, b) => sum + b.length, 0)
    const combined = new Uint8Array(totalLength)
    let offset = 0
    for (const chunk of this.chunks) {
      combined.set(chunk, offset)
      offset += chunk.length
    }
    this.chunks = []

    try {
      const audioBuffer = await this.audioContext.decodeAudioData(combined.buffer)
      this.bufferQueue.push(audioBuffer)
      this.totalDuration += audioBuffer.duration
      this.startTime = this.audioContext.currentTime
      this._isPlaying = true
      this.playNextBuffer()
    } catch (err) {
      console.error('[AudioSync] decodeAudioData failed:', err)
    }
  }

  private playNextBuffer(): void {
    if (!this.audioContext || !this.gainNode) return
    if (this.bufferQueue.length === 0) {
      this._isPlaying = false
      return
    }

    const buffer = this.bufferQueue.shift()!
    this.source = this.audioContext.createBufferSource()
    this.source.buffer = buffer
    this.source.connect(this.gainNode)
    this.source.onended = () => {
      if (this._isPlaying) {
        this.playNextBuffer()
      }
    }
    this.source.start(0)
  }

  pause(): void {
    if (!this._isPlaying || !this.audioContext) return
    this.pausedAt = this.audioContext.currentTime - this.startTime + this.pausedAt
    this.source?.stop()
    this._isPlaying = false
  }

  resume(): void {
    this.play()
  }

  stop(): void {
    this.source?.stop()
    this.source?.disconnect()
    this.source = null
    this._isPlaying = false
    this.pausedAt = 0
    this.totalDuration = 0
    this.bufferQueue = []
    this.chunks = []
    this.startTime = 0
  }

  async ensureResumed(): Promise<void> {
    await this.init()
    if (this.audioContext?.state === 'suspended') {
      await this.audioContext.resume()
    }
  }

  destroy(): void {
    this.stop()
    this.gainNode?.disconnect()
    this.gainNode = null
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
  }
}
