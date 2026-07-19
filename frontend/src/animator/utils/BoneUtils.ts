import { Bone, type Object3D } from 'three'
import type { BoneMap, BoneName } from '../types'

export function buildBoneMap(skeleton: Object3D): BoneMap {
  const map: BoneMap = {}
  const boneNames: BoneName[] = [
    'spine', 'spine1', 'spine2', 'head', 'neck',
    'leftEye', 'rightEye', 'leftArm', 'rightArm',
    'leftForeArm', 'rightForeArm', 'leftShoulder', 'rightShoulder',
  ]

  const allBoneNames: string[] = []

  skeleton.traverse((child: Object3D) => {
    if (child instanceof Bone) {
      allBoneNames.push(child.name)
      for (const name of boneNames) {
        if (child.name === name || child.name.toLowerCase() === name.toLowerCase()) {
          map[name] = child
          break
        }
      }
    }
  })

  console.log(`[BoneUtils] Found bones: ${allBoneNames.join(', ')}`)
  const matched = Object.entries(map).filter(([, v]) => v).map(([k]) => k)
  console.log(`[BoneUtils] Matched: ${matched.length > 0 ? matched.join(', ') : '(none)'}`)
  const missing = boneNames.filter(n => !map[n])
  if (missing.length > 0) {
    console.warn(`[BoneUtils] Missing bones: ${missing.join(', ')}`)
  }

  return map
}

export function getBone(map: BoneMap, name: BoneName): Bone | undefined {
  return map[name] as Bone | undefined
}

export function hasBone(map: BoneMap, name: BoneName): boolean {
  return map[name] !== undefined
}

export function getBoneNames(): BoneName[] {
  return [
    'spine', 'spine1', 'spine2', 'head', 'neck',
    'leftEye', 'rightEye', 'leftArm', 'rightArm',
    'leftForeArm', 'rightForeArm', 'leftShoulder', 'rightShoulder',
  ]
}

export function storeRestPose(boneMap: BoneMap): Map<string, { position: [number, number, number]; rotation: [number, number, number] }> {
  const rest = new Map<string, { position: [number, number, number]; rotation: [number, number, number] }>()
  for (const name of getBoneNames()) {
    const bone = boneMap[name]
    if (bone) {
      rest.set(name, {
        position: [bone.position.x, bone.position.y, bone.position.z],
        rotation: [bone.rotation.x, bone.rotation.y, bone.rotation.z],
      })
    }
  }
  return rest
}
