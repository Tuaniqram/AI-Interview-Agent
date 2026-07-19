import * as THREE from 'three';

export type BodyState = 'idle' | 'speaking' | 'listening' | 'thinking';

function smoothstep(t: number): number {
  return t * t * (3 - 2 * t);
}

interface BoneRest {
  px: number; py: number; pz: number;
  rx: number; ry: number; rz: number;
}

type BoneName =
  | 'Spine' | 'Spine1' | 'Spine2'
  | 'Head'
  | 'LeftEye' | 'RightEye'
  | 'LeftArm' | 'RightArm'
  | 'LeftForeArm' | 'RightForeArm';

// Universal arm-lowering offset — GLB rest pose has arms slightly raised
const ARM_DOWN: Record<string, { rx: number; ry: number; rz: number }> = {
  LeftArm: { rx: 1.2, ry: 0, rz: 0 },
  RightArm: { rx: 1.2, ry: 0, rz: 0 },
  LeftForeArm: { rx: 0.2, ry: 0, rz: 0 },
  RightForeArm: { rx: 0.2, ry: 0, rz: 0 },
};

// Per-state base offsets from rest pose (applied on top of ARM_DOWN and continuous)
const STATE_OFFSETS: Record<BodyState, Partial<Record<BoneName, { rx: number; ry: number; rz: number }>>> = {
  idle: {},
  speaking: {
    Head: { rx: 0.04, ry: 0, rz: 0 },
    LeftArm: { rx: 0.05, ry: 0, rz: 0.02 },
    RightArm: { rx: 0.05, ry: 0, rz: -0.02 },
    LeftForeArm: { rx: 0.08, ry: 0, rz: 0 },
    RightForeArm: { rx: 0.08, ry: 0, rz: 0 },
  },
  listening: {
    Head: { rx: 0.02, ry: 0, rz: 0.03 },
  },
  thinking: {
    Head: { rx: -0.03, ry: 0.03, rz: -0.02 },
    LeftArm: { rx: 0.15, ry: 0.03, rz: 0.05 },
    LeftForeArm: { rx: 0.3, ry: 0, rz: 0 },
  },
};

const ALL_BONES: BoneName[] = [
  'Spine', 'Spine1', 'Spine2',
  'Head', 'LeftEye', 'RightEye',
  'LeftArm', 'RightArm', 'LeftForeArm', 'RightForeArm',
];

export class BodyAnimator {
  private bones: Map<string, THREE.Bone>;
  private rests = new Map<string, BoneRest>();
  private currentState: BodyState = 'idle';
  private blend = 1;

  constructor(bones: Map<string, THREE.Bone>) {
    this.bones = bones;
    for (const name of ALL_BONES) {
      const b = bones.get(name);
      if (b) {
        this.rests.set(name, {
          px: b.position.x, py: b.position.y, pz: b.position.z,
          rx: b.rotation.x, ry: b.rotation.y, rz: b.rotation.z,
        });
      }
    }
  }

  private lastTime = 0;

  update(time: number, state: BodyState) {
    const dt = this.lastTime === 0 ? 0.016 : time - this.lastTime;
    this.lastTime = time;

    if (state !== this.currentState) {
      this.currentState = state;
      this.blend = 0;
    }
    this.blend = Math.min(1, this.blend + dt * 2.5);

    // Continuous animations
    const cont = this.computeContinuous(time);

    // State blend factor
    const sb = smoothstep(this.blend);

    // State offsets (target, interpolated from zero)
    const targetOffsets = STATE_OFFSETS[state];
    const stateOffsets: Record<string, { rx: number; ry: number; rz: number }> = {};
    for (const name of ALL_BONES) {
      const o = targetOffsets[name];
      if (o) {
        stateOffsets[name] = { rx: o.rx * sb, ry: o.ry * sb, rz: o.rz * sb };
      }
    }

    // Gesture offset for speaking arms
    const gestureOffset = this.computeGestureOffset(time, state);

    // Apply to bones
    for (const [name, bone] of this.bones) {
      const rest = this.rests.get(name);
      if (!rest) continue;

      const c = cont[name] || { py: 0, rx: 0, ry: 0, rz: 0 };
      const s = stateOffsets[name] || { rx: 0, ry: 0, rz: 0 };
      const g = gestureOffset[name] || { rx: 0, ry: 0, rz: 0 };
      const a = ARM_DOWN[name] || { rx: 0, ry: 0, rz: 0 };

      bone.position.set(rest.px, rest.py + c.py, rest.pz);
      bone.rotation.set(
        rest.rx + c.rx + a.rx + s.rx + g.rx,
        rest.ry + c.ry + a.ry + s.ry + g.ry,
        rest.rz + c.rz + a.rz + s.rz + g.rz,
      );
    }
  }

  private computeContinuous(time: number) {
    const r: Record<string, { py: number; rx: number; ry: number; rz: number }> = {};

    const breathe = Math.sin(time * 2.5);
    for (const name of ['Spine', 'Spine1', 'Spine2'] as BoneName[]) {
      r[name] = {
        py: breathe * 0.006,
        rx: breathe * 0.005,
        ry: 0,
        rz: Math.sin(time * 1.3) * 0.003,
      };
    }

    r.Head = {
      py: 0,
      rx: Math.sin(time * 0.3) * 0.008,
      ry: 0,
      rz: Math.sin(time * 0.4) * 0.015,
    };

    for (const eye of ['LeftEye', 'RightEye'] as BoneName[]) {
      const phase = eye === 'LeftEye' ? 0 : 1;
      r[eye] = {
        py: 0,
        rx: Math.sin(time * 0.2 + phase) * 0.03,
        ry: Math.sin(time * 0.15 + phase * 0.5) * 0.03,
        rz: 0,
      };
    }

    for (const side of ['Left', 'Right'] as ('Left' | 'Right')[]) {
      const arm = `${side}Arm` as BoneName;
      const phase = side === 'Left' ? 0 : 1.5;
      r[arm] = {
        py: 0,
        rx: Math.sin(time * 0.2 + phase) * 0.008,
        ry: 0,
        rz: Math.sin(time * 0.15) * 0.005,
      };
    }

    return r;
  }

  private computeGestureOffset(time: number, state: BodyState) {
    const r: Record<string, { rx: number; ry: number; rz: number }> = {};

    if (state !== 'speaking') return r;

    // Subtle arm gesture during speaking
    const gest = 2.0;
    for (const side of ['Left', 'Right'] as ('Left' | 'Right')[]) {
      const arm = `${side}Arm` as BoneName;
      const phase = side === 'Left' ? 0 : 1.5;
      r[arm] = {
        rx: Math.sin(time * gest + phase) * 0.06,
        ry: 0,
        rz: Math.sin(time * gest * 0.7 + phase * 0.3) * 0.04,
      };

      const fore = `${side}ForeArm` as BoneName;
      r[fore] = {
        rx: Math.sin(time * gest * 0.5 + (side === 'Left' ? 1 : 2)) * 0.04,
        ry: 0,
        rz: 0,
      };
    }

    // Head nod on top of state offset
    r.Head = r.Head || { rx: 0, ry: 0, rz: 0 };
    r.Head.rx += Math.sin(time * 2.5) * 0.015;

    return r;
  }
}
