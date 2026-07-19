import { MathUtils } from 'three'
import type { BoneTransform } from '../types'
import { CONFIG } from './Config'

const _v = { x: 0, y: 0, z: 0 }

export function damp(
  current: number,
  target: number,
  lambda: number,
  delta: number,
): number {
  return current + (target - current) * (1 - Math.exp(-lambda * delta))
}

export function dampAngle(
  current: number,
  target: number,
  lambda: number,
  delta: number,
): number {
  let diff = target - current
  while (diff > Math.PI) diff -= Math.PI * 2
  while (diff < -Math.PI) diff += Math.PI * 2
  return current + diff * (1 - Math.exp(-lambda * delta))
}

export function dampTransform(
  current: BoneTransform,
  target: BoneTransform,
  lambda: number,
  delta: number,
): BoneTransform {
  const cr = current.rotation ?? [0, 0, 0]
  const tr = target.rotation ?? [0, 0, 0]
  const cp = current.position ?? [0, 0, 0]
  const tp = target.position ?? [0, 0, 0]

  _v.x = dampAngle(cr[0], tr[0], lambda, delta)
  _v.y = dampAngle(cr[1], tr[1], lambda, delta)
  _v.z = dampAngle(cr[2], tr[2], lambda, delta)
  const rotation: [number, number, number] = [_v.x, _v.y, _v.z]

  _v.x = damp(cp[0], tp[0], lambda, delta)
  _v.y = damp(cp[1], tp[1], lambda, delta)
  _v.z = damp(cp[2], tp[2], lambda, delta)
  const position: [number, number, number] = [_v.x, _v.y, _v.z]

  return {
    rotation: rotation.some((v) => v !== 0) ? rotation : undefined,
    position: position.some((v) => v !== 0) ? position : undefined,
  }
}

export function smoothstep(t: number): number {
  return MathUtils.smoothstep(t, 0, 1)
}

export function lerp(a: number, b: number, t: number): number {
  return MathUtils.lerp(a, b, t)
}

export function clamp(val: number, min: number, max: number): number {
  return MathUtils.clamp(val, min, max)
}

export const FAST_DAMP = CONFIG.StateTransition.BlendDuration * 2
export const MEDIUM_DAMP = CONFIG.StateTransition.BlendDuration
export const SLOW_DAMP = CONFIG.StateTransition.BlendDuration * 0.5
