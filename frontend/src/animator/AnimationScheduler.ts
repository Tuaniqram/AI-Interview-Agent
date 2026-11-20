import type { ScheduledTimer } from './types'
import { randomRange } from './utils/Random'

let nextId = 1

export class AnimationScheduler {
  private timers: ScheduledTimer[] = []
  private paused = false

  setTimeout(callback: () => void, delay: number): number {
    const id = nextId++
    this.timers.push({ id, remaining: delay, callback, repeat: false, repeatInterval: 0 })
    return id
  }

  setInterval(callback: () => void, interval: number): number {
    const id = nextId++
    this.timers.push({ id, remaining: interval, callback, repeat: true, repeatInterval: interval })
    return id
  }

  scheduleRandom(callback: () => void, minDelay: number, maxDelay: number): number {
    return this.setTimeout(callback, randomRange(minDelay, maxDelay))
  }

  cancel(id: number): void {
    const idx = this.timers.findIndex((t) => t.id === id)
    if (idx >= 0) {
      this.timers.splice(idx, 1)
    }
  }

  cancelAll(): void {
    this.timers.length = 0
  }

  pause(): void {
    this.paused = true
  }

  resume(): void {
    this.paused = false
  }

  update(delta: number): void {
    if (this.paused || this.timers.length === 0) return

    for (let i = this.timers.length - 1; i >= 0; i--) {
      const timer = this.timers[i]
      timer.remaining -= delta

      if (timer.remaining <= 0) {
        timer.callback()
        if (timer.repeat) {
          timer.remaining = timer.repeatInterval
        } else {
          this.timers.splice(i, 1)
        }
      }
    }
  }

  get pendingCount(): number {
    return this.timers.length
  }
}
