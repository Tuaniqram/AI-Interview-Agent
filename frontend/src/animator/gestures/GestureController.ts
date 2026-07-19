import type { GestureTypeName, GestureDefinition, GestureRuntime, GestureBoneTarget, GestureDebugFrame } from './GestureTypes'
import { GESTURE_LIBRARY } from './GestureLibrary'
import { computePhaseTargets, damp, getPhaseLabel, debugGesture, createFallbackTargets } from './GestureBlender'

export const GESTURE_TYPE_NAMES: GestureTypeName[] = Object.keys(GESTURE_LIBRARY) as GestureTypeName[]

export class GestureController {
  private runtime: GestureRuntime = { active: false, type: null, phaseIndex: 0, phaseTime: 0, elapsed: 0 }
  private currentDef: GestureDefinition | null = null
  private computedOffsets: Record<string, GestureBoneTarget> = {}
  private returning = false
  private returnVelocities: Map<string, [number, number, number]> = new Map()
  private availableBones: Set<string> = new Set()
  private debugFrame: GestureDebugFrame | null = null

  private readonly RETURN_LAMBDA = 5
  private readonly RETURN_THRESHOLD = 0.0001

  setAvailableBones(bones: string[]): void {
    this.availableBones = new Set(bones)
  }

  triggerGesture(type: GestureTypeName): boolean {
    if (this.runtime.active) {
      debugGesture(`Cannot start "${type}" — gesture "${this.runtime.type}" is active`)
      return false
    }

    const def = GESTURE_LIBRARY[type]
    if (!def) {
      console.warn(`[GestureController] Unknown gesture type: "${type}"`)
      return false
    }

    const resolvedDef = this.availableBones.size > 0
      ? createFallbackTargets(def, this.availableBones)
      : def

    this.currentDef = resolvedDef
    this.runtime = { active: true, type, phaseIndex: 0, phaseTime: 0, elapsed: 0 }
    this.returning = false
    this.returnVelocities.clear()
    this.computedOffsets = {}

    debugGesture(`START "${type}" — ${resolvedDef.phases.length} phases: ${resolvedDef.phases.map((p, i) => `${getPhaseLabel(i, resolvedDef.phases.length)}(${p.duration.toFixed(2)}s)`).join(' → ')}`)

    return true
  }

  stopGesture(): void {
    if (!this.runtime.active) return

    const affectedBones = this.collectAffectedBones()
    for (const boneName of affectedBones) {
      const current = this.computedOffsets[boneName]?.rotation ?? [0, 0, 0]
      this.returnVelocities.set(boneName, [current[0], current[1], current[2]])
    }

    this.runtime.active = false
    this.runtime.type = null
    this.returning = true
    debugGesture('STOP — beginning return to neutral')
  }

  isAnyGestureActive(): boolean {
    return this.runtime.active || this.returning
  }

  getCurrentGesture(): GestureTypeName | null {
    return this.runtime.type
  }

  getDebugFrame(): GestureDebugFrame | null {
    return this.debugFrame
  }

  update(delta: number): void {
    if (this.returning) {
      this.updateReturn(delta)
      return
    }

    if (!this.runtime.active || !this.currentDef) {
      this.computedOffsets = {}
      this.debugFrame = null
      return
    }

    const def = this.currentDef
    const phase = def.phases[this.runtime.phaseIndex]
    if (!phase) {
      this.beginReturn()
      return
    }

    this.runtime.elapsed += delta
    this.runtime.phaseTime += delta

    const phaseProgress = this.runtime.phaseTime / phase.duration
    this.computedOffsets = computePhaseTargets(phase, phaseProgress)

    const bones = Object.keys(phase.targets)
    const labels = ['anticipation', 'attack', 'hold', 'release', 'followThrough']
    const stateLabel = labels[this.runtime.phaseIndex] ?? `phase_${this.runtime.phaseIndex}`

    if (typeof window !== 'undefined' && (window as any).DEBUG_GESTURES) {
      this.debugFrame = {
        gesture: def.name,
        state: stateLabel,
        progress: Math.min(1, phaseProgress),
        bones,
        targets: this.computedOffsets,
        phaseIndex: this.runtime.phaseIndex,
        elapsed: this.runtime.elapsed,
      }

      const rotStr = bones.map(b => {
        const r = this.computedOffsets[b]?.rotation
        return r ? `${b}: [${r.map(v => v.toFixed(3)).join(', ')}]` : b
      }).join(', ')

      console.log(
        `[GESTURE] ${def.name.padEnd(18)} │ ${stateLabel.padEnd(14)} │ ` +
        `t:${Math.min(1, phaseProgress).toFixed(2)} │ ${rotStr}`
      )
    }

    if (phaseProgress >= 1) {
      this.runtime.phaseIndex++
      this.runtime.phaseTime = 0

      if (this.runtime.phaseIndex >= def.phases.length) {
        const affectedBones = this.collectAffectedBones()
        for (const boneName of affectedBones) {
          const current = this.computedOffsets[boneName]?.rotation ?? [0, 0, 0]
          this.returnVelocities.set(boneName, [current[0], current[1], current[2]])
        }
        this.runtime.active = false
        this.runtime.type = null
        this.returning = true
        debugGesture(`END "${def.name}" — returning neutral`)
      }
    }
  }

  getBoneOffsets(): Readonly<Record<string, GestureBoneTarget>> {
    return this.computedOffsets
  }

  private updateReturn(delta: number): void {
    let allZero = true
    const newOffsets: Record<string, GestureBoneTarget> = {}

    for (const [boneName, velocity] of this.returnVelocities.entries()) {
      const vx = damp(velocity[0], 0, this.RETURN_LAMBDA, delta)
      const vy = damp(velocity[1], 0, this.RETURN_LAMBDA, delta)
      const vz = damp(velocity[2], 0, this.RETURN_LAMBDA, delta)

      this.returnVelocities.set(boneName, [vx, vy, vz])

      if (Math.abs(vx) > this.RETURN_THRESHOLD ||
          Math.abs(vy) > this.RETURN_THRESHOLD ||
          Math.abs(vz) > this.RETURN_THRESHOLD) {
        allZero = false
      }

      newOffsets[boneName] = { rotation: [vx, vy, vz] }
    }

    this.computedOffsets = newOffsets

    if (typeof window !== 'undefined' && (window as any).DEBUG_GESTURES) {
      const activeCount = Array.from(this.returnVelocities.values()).filter(
        v => Math.abs(v[0]) > this.RETURN_THRESHOLD || Math.abs(v[1]) > this.RETURN_THRESHOLD || Math.abs(v[2]) > this.RETURN_THRESHOLD
      ).length
      if (activeCount > 0) {
        console.log(`[GESTURE] return → damping ${activeCount} bones ...`)
      }
    }

    if (allZero) {
      this.returning = false
      this.returnVelocities.clear()
      this.computedOffsets = {}
      this.debugFrame = null
      debugGesture('RETURN COMPLETE — neutral pose')
    }
  }

  private beginReturn(): void {
    const affectedBones = this.collectAffectedBones()
    for (const boneName of affectedBones) {
      const current = this.computedOffsets[boneName]?.rotation ?? [0, 0, 0]
      this.returnVelocities.set(boneName, [current[0], current[1], current[2]])
    }
    this.runtime.active = false
    this.runtime.type = null
    this.returning = true
    debugGesture('FORCE RETURN — no more phases')
  }

  private collectAffectedBones(): string[] {
    if (!this.currentDef) return []
    const bones = new Set<string>()
    for (const phase of this.currentDef.phases) {
      for (const boneName of Object.keys(phase.targets)) {
        bones.add(boneName)
      }
    }
    return Array.from(bones)
  }
}
