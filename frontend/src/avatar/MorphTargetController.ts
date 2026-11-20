import type { Mesh } from 'three'

const EMA_FACTOR = 0.25

export class MorphTargetController {
  private meshes: Mesh[] = []
  private prevValues: Map<string, number[]> = new Map()

  setMeshes(meshes: Mesh[]): void {
    this.meshes = meshes
    this.prevValues.clear()
  }

  applyTargets(targets: Record<string, number>): void {
    for (const mesh of this.meshes) {
      if (!mesh.morphTargetInfluences || !mesh.morphTargetDictionary) continue

      const dict = mesh.morphTargetDictionary as Record<string, number>
      const influences = mesh.morphTargetInfluences
      const key = mesh.uuid
      let prev = this.prevValues.get(key)

      if (!prev) {
        prev = new Array(influences.length).fill(0)
        this.prevValues.set(key, prev)
      }

      for (const [name, idx] of Object.entries(dict)) {
        const target = targets[name] ?? 0
        const current = prev[idx]
        const smoothed = current + (target - current) * EMA_FACTOR
        influences[idx] = smoothed
        prev[idx] = smoothed
      }
    }
  }

  mergeTargets(
    primary: Record<string, number>,
    secondary: Record<string, number>,
    secondaryWeight = 1,
  ): Record<string, number> {
    const merged: Record<string, number> = { ...primary }

    for (const [key, val] of Object.entries(secondary)) {
      if (merged[key] !== undefined) {
        merged[key] = Math.max(merged[key], val * secondaryWeight)
      } else {
        merged[key] = val * secondaryWeight
      }
    }

    return merged
  }

  clearTargets(): void {
    for (const mesh of this.meshes) {
      if (!mesh.morphTargetInfluences) continue
      for (let i = 0; i < mesh.morphTargetInfluences.length; i++) {
        mesh.morphTargetInfluences[i] = 0
      }
    }
    this.prevValues.clear()
  }
}
