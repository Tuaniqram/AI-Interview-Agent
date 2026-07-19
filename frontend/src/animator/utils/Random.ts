export class RandomTimer {
  private elapsed = 0
  private currentInterval: number
  private seed: number

  constructor(
    private minInterval: number,
    private maxInterval: number,
    seed?: number,
  ) {
    this.seed = seed ?? Math.random()
    this.currentInterval = this.nextInterval()
  }

  update(delta: number): boolean {
    this.elapsed += delta
    if (this.elapsed >= this.currentInterval) {
      this.elapsed = 0
      this.currentInterval = this.nextInterval()
      return true
    }
    return false
  }

  reset(): void {
    this.elapsed = 0
    this.currentInterval = this.nextInterval()
  }

  private nextInterval(): number {
    const range = this.maxInterval - this.minInterval
    this.seed = (this.seed * 16807) % 2147483647
    return this.minInterval + (this.seed / 2147483647) * range
  }

  get progress(): number {
    return Math.min(1, this.elapsed / this.currentInterval)
  }
}

export class RandomValue {
  private value: number
  private elapsed = 0
  private holdTime: number

  constructor(
    private minValue: number,
    private maxValue: number,
    private minHold: number,
    private maxHold: number,
    private onChange?: (value: number) => void,
  ) {
    this.value = this.nextValue()
    this.holdTime = this.nextHold()
  }

  update(delta: number): number {
    this.elapsed += delta
    if (this.elapsed >= this.holdTime) {
      this.value = this.nextValue()
      this.holdTime = this.nextHold()
      this.elapsed = 0
      this.onChange?.(this.value)
    }
    return this.value
  }

  private nextValue(): number {
    return this.minValue + Math.random() * (this.maxValue - this.minValue)
  }

  private nextHold(): number {
    return this.minHold + Math.random() * (this.maxHold - this.minHold)
  }

  get current(): number {
    return this.value
  }
}

export function randomRange(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

export function randomBool(probability: number): boolean {
  return Math.random() < probability
}

export function randomInt(min: number, max: number): number {
  return Math.floor(randomRange(min, max + 1))
}
