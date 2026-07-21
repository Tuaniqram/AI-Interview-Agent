import { useRef, useEffect, useCallback, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { VisemeFrame } from '../types/voice';
import type { AvatarEmotion } from '../types/avatar';
import {
  visemeToBlendShapes,
  emotionToBlendShapes,
  silenceBlendShapes,
} from '../utils/visemeMapper';
import { BodyAnimator } from '../animator/BodyAnimator';
import type { BodyState } from '../animator/types';
import { buildBoneMap } from '../animator/utils/BoneUtils';
import { LipSyncController } from '../avatar/LipSyncController';
import { Loader2 } from 'lucide-react';

const GLB_PATH = '/models/avatarv2.glb';

// Morph target names from avatarv2.glb extras.targetNames — exact per-mesh arrays
const MORPH_NAMES_BY_MESH: Record<string, string[]> = {
  AvatarHead: [
    'browDownLeft', 'browDownRight', 'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight',
    'cheekPuff', 'cheekSquintLeft', 'cheekSquintRight',
    'eyeBlinkLeft', 'eyeBlinkRight',
    'eyeLookDownLeft', 'eyeLookDownRight', 'eyeLookInLeft', 'eyeLookInRight',
    'eyeLookOutLeft', 'eyeLookOutRight', 'eyeLookUpLeft', 'eyeLookUpRight',
    'eyeSquintLeft', 'eyeSquintRight', 'eyeWideLeft', 'eyeWideRight',
    'jawForward', 'jawLeft', 'jawOpen', 'jawRight',
    'mouthClose', 'mouthDimpleLeft', 'mouthDimpleRight',
    'mouthFrownLeft', 'mouthFrownRight', 'mouthFunnel',
    'mouthLeft', 'mouthLowerDownLeft', 'mouthLowerDownRight',
    'mouthPressLeft', 'mouthPressRight', 'mouthPucker',
    'mouthRight', 'mouthRollLower', 'mouthRollUpper',
    'mouthShrugLower', 'mouthShrugUpper',
    'mouthSmileLeft', 'mouthSmileRight',
    'mouthStretchLeft', 'mouthStretchRight',
    'mouthUpperUpLeft', 'mouthUpperUpRight',
    'noseSneerLeft', 'noseSneerRight',
    'CH', 'DD', 'E', 'FF', 'PP', 'RR', 'SS', 'TH', 'aa', 'ih', 'kk', 'nn', 'oh', 'ou', 'sil',
  ],
  AvatarEyelashes: [
    'browDownLeft', 'browDownRight', 'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight',
    'cheekSquintLeft', 'cheekSquintRight',
    'eyeBlinkLeft', 'eyeBlinkRight',
    'eyeLookDownLeft', 'eyeLookDownRight', 'eyeLookInLeft', 'eyeLookInRight',
    'eyeLookOutLeft', 'eyeLookOutRight', 'eyeLookUpLeft', 'eyeLookUpRight',
    'eyeSquintLeft', 'eyeSquintRight', 'eyeWideLeft', 'eyeWideRight',
    'mouthDimpleLeft', 'mouthDimpleRight',
    'mouthLeft', 'mouthRight',
    'mouthSmileLeft', 'mouthSmileRight',
    'noseSneerLeft', 'noseSneerRight',
  ],
  AvatarTeethLower: [
    'jawForward', 'jawLeft', 'jawOpen', 'jawRight',
    'CH', 'DD', 'E', 'FF', 'PP', 'RR', 'SS', 'TH', 'aa', 'ih', 'kk', 'nn', 'oh', 'ou', 'sil',
  ],
};

interface AvatarRendererProps {
  emotion?: AvatarEmotion;
  activeViseme?: VisemeFrame | null;
  isSpeaking?: boolean;
  isListening?: boolean;
  className?: string;
}

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

function buildProceduralHead(): THREE.Group {
  const group = new THREE.Group();

  const skinColor = 0xd4a574;
  const hairColor = 0x2c1810;
  const shirtColor = 0x3b3b5c;

  const headGeom = new THREE.SphereGeometry(0.7, 48, 48);
  const headMat = new THREE.MeshStandardMaterial({
    color: skinColor,
    roughness: 0.55,
    metalness: 0.0,
  });

  const pos = headGeom.attributes.position.array as Float32Array;
  const morphDeltas: Float32Array[] = [];
  const morphNames: string[] = [];

  function addMorph(
    name: string,
    compute: (_x: number, _y: number, _z: number, _r: number, _phi: number) => [number, number, number],
  ) {
    const delta = new Float32Array(pos.length);
    for (let i = 0; i < pos.length; i += 3) {
      const x = pos[i];
      const y = pos[i + 1];
      const z = pos[i + 2];
      const r = Math.sqrt(x * x + y * y + z * z);
      const phi = Math.atan2(z, x);
      const [dx, dy, dz] = compute(x, y, z, r, phi);
      delta[i] = dx;
      delta[i + 1] = dy;
      delta[i + 2] = dz;
    }
    morphDeltas.push(delta);
    morphNames.push(name);
  }

  addMorph('jawOpen', (_x, y, z) => {
    if (y < -0.15 && z > 0) {
      const t = smoothstep(-0.15, -0.6, y) * smoothstep(0, 0.5, z);
      return [0, -0.25 * t, 0];
    }
    return [0, 0, 0];
  });
  addMorph('eyeBlinkLeft', (x, y, z) => {
    if (x < -0.1 && x > -0.4 && y > 0.12 && y < 0.38 && z > 0.45) {
      const t = smoothstep(-0.1, -0.25, x) * smoothstep(-0.4, -0.25, x) *
                smoothstep(0.12, 0.25, y) * smoothstep(0.38, 0.25, y) * smoothstep(0.45, 0.6, z);
      return [0, -0.15 * t, 0];
    }
    return [0, 0, 0];
  });
  addMorph('eyeBlinkRight', (x, y, z) => {
    if (x > 0.1 && x < 0.4 && y > 0.12 && y < 0.38 && z > 0.45) {
      const t = smoothstep(0.1, 0.25, x) * smoothstep(0.4, 0.25, x) *
                smoothstep(0.12, 0.25, y) * smoothstep(0.38, 0.25, y) * smoothstep(0.45, 0.6, z);
      return [0, -0.15 * t, 0];
    }
    return [0, 0, 0];
  });
  addMorph('mouthSmile', (x, y, z) => {
    if (Math.abs(x) > 0.12 && Math.abs(y) < 0.18 && z > 0.3) {
      const t = smoothstep(0.12, 0.3, Math.abs(x)) * smoothstep(0.3, 0.6, z) * smoothstep(0.18, 0.05, Math.abs(y));
      return [0, 0.2 * t, 0];
    }
    return [0, 0, 0];
  });
  addMorph('browDownLeft', (x, y, z) => {
    if (x < -0.1 && y > 0.38 && z > 0.25) {
      const t = smoothstep(-0.1, -0.4, x) * smoothstep(0.38, 0.55, y) * smoothstep(0.25, 0.6, z);
      return [0, -0.22 * t, 0];
    }
    return [0, 0, 0];
  });
  addMorph('browDownRight', (x, y, z) => {
    if (x > 0.1 && y > 0.38 && z > 0.25) {
      const t = smoothstep(0.1, 0.4, x) * smoothstep(0.38, 0.55, y) * smoothstep(0.25, 0.6, z);
      return [0, -0.22 * t, 0];
    }
    return [0, 0, 0];
  });
  addMorph('browInnerUp', (x, y, z) => {
    if (Math.abs(x) < 0.18 && y > 0.38 && z > 0.3) {
      const t = smoothstep(0.18, 0, Math.abs(x)) * smoothstep(0.38, 0.55, y) * smoothstep(0.3, 0.6, z);
      return [0, 0.18 * t, 0];
    }
    return [0, 0, 0];
  });
  addMorph('mouthOpen', (_x, y, z) => {
    if (Math.abs(y) < 0.25 && z > 0.3) {
      const t = smoothstep(0.3, 0.6, z) * smoothstep(0.25, 0, Math.abs(y));
      return [0, (y >= 0 ? 1 : -1) * 0.18 * t, 0];
    }
    return [0, 0, 0];
  });
  addMorph('mouthFunnel', (x, y, z) => {
    if (Math.abs(x) < 0.25 && Math.abs(y) < 0.22 && z > 0.25) {
      const t = smoothstep(0.25, 0, Math.abs(x)) * smoothstep(0.25, 0.6, z) * smoothstep(0.22, 0.05, Math.abs(y));
      return [-x * 0.3 * t, -y * 0.3 * t, 0.18 * t];
    }
    return [0, 0, 0];
  });
  addMorph('mouthPucker', (x, y, z) => {
    if (Math.abs(x) < 0.18 && Math.abs(y) < 0.18 && z > 0.3) {
      const t = smoothstep(0.18, 0, Math.abs(x)) * smoothstep(0.3, 0.6, z) * smoothstep(0.18, 0.05, Math.abs(y));
      return [0, 0, 0.22 * t];
    }
    return [0, 0, 0];
  });
  addMorph('mouthClose', (_x, y, z) => {
    if (Math.abs(y) < 0.15 && z > 0.35) {
      const t = smoothstep(0.35, 0.65, z) * smoothstep(0.15, 0, Math.abs(y));
      return [0, (y >= 0 ? -1 : 1) * 0.12 * t, 0];
    }
    return [0, 0, 0];
  });

  headGeom.morphAttributes.position = morphDeltas.map(
    (d) => new THREE.Float32BufferAttribute(d, 3),
  );

  const headMesh = new THREE.Mesh(headGeom, headMat);
  headMesh.morphTargetDictionary = Object.fromEntries(morphNames.map((n, i) => [n, i]));
  headMesh.morphTargetInfluences = new Array(morphNames.length).fill(0);
  group.add(headMesh);

  const eyeMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.2, metalness: 0.0 });
  const pupilMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.5, metalness: 0.0 });

  const addEye = (side: 1 | -1) => {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.08, 16, 16), eyeMat);
    eye.position.set(side * 0.22, 0.25, 0.55);
    eye.name = side === -1 ? 'eye-left' : 'eye-right';
    group.add(eye);
    const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.04, 12, 12), pupilMat);
    pupil.position.set(0, 0, 0.04);
    eye.add(pupil);
    return eye;
  };
  addEye(-1); addEye(1);

  const skinMat = new THREE.MeshStandardMaterial({ color: skinColor, roughness: 0.55, metalness: 0.0 });

  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.2, 0.35, 24), skinMat);
  neck.position.set(0, -0.85, 0);
  group.add(neck);

  for (const s of [-1, 1]) {
    const ear = new THREE.Mesh(new THREE.SphereGeometry(0.1, 12, 12), skinMat);
    ear.position.set(s * 0.68, 0.15, 0.0);
    ear.scale.set(0.6, 1, 0.5);
    group.add(ear);
  }

  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.18, 12), skinMat);
  nose.position.set(0, 0.08, 0.68);
  nose.rotation.x = Math.PI * 0.5;
  group.add(nose);

  const browMat = new THREE.MeshStandardMaterial({ color: hairColor, roughness: 0.7, metalness: 0.0 });
  for (const side of [-1, 1]) {
    const brow = new THREE.Mesh(new THREE.CapsuleGeometry(0.02, 0.12, 4, 8), browMat);
    brow.position.set(side * 0.22, 0.42, 0.52);
    brow.rotation.z = side * 0.15;
    group.add(brow);
  }

  const hair = new THREE.Mesh(
    new THREE.SphereGeometry(0.72, 48, 24, 0, Math.PI * 2, 0, Math.PI * 0.5),
    new THREE.MeshStandardMaterial({ color: hairColor, roughness: 0.8, metalness: 0.0 }),
  );
  hair.position.set(0, 0.05, 0);
  group.add(hair);

  const shoulders = new THREE.Mesh(
    new THREE.CylinderGeometry(0.45, 0.4, 0.3, 24),
    new THREE.MeshStandardMaterial({ color: shirtColor, roughness: 0.6, metalness: 0.0 }),
  );
  shoulders.position.set(0, -1.2, 0);
  group.add(shoulders);

  group.position.set(0, -0.5, 0);
  return group;
}

function centerAndScaleModel(model: THREE.Object3D) {
  const box = new THREE.Box3().setFromObject(model);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());

  const targetHeight = 4.0;
  const s = targetHeight / size.y;
  model.scale.setScalar(s);

  model.position.set(0, 0, 0);
  const scaledCenter = new THREE.Vector3(
    center.x * s,
    center.y * s,
    center.z * s,
  );
  model.position.sub(scaledCenter);
  model.position.y += 1.2;
}

function setupMorphTargets(child: THREE.Mesh) {
  const geom = child.geometry as THREE.BufferGeometry;
  const count = geom.morphAttributes?.position?.length || 0;
  if (count === 0) return;

  const names = MORPH_NAMES_BY_MESH[child.name];
  if (names && names.length !== count) {
    console.warn(`[Avatar] ${child.name}: expected ${names.length} morph names, got ${count} targets — using numeric`);
  }

  const targetNames = names && names.length === count
    ? names
    : Array.from({ length: count }, (_, i) => String(i));

  child.updateMorphTargets();
  child.morphTargetDictionary = Object.fromEntries(targetNames.map((n, i) => [n, i]));
  child.morphTargetInfluences = new Array(count).fill(0);

  if (child.material) {
    (child.material as unknown as { morphTargets: boolean }).morphTargets = true;
  }

  console.log(`[Avatar] ${child.name}: ${count} morph targets ready`);
}

let _globalLipSync: LipSyncController | null = new LipSyncController()

export function getLipSyncController(): LipSyncController | null {
  return _globalLipSync
}

const DEBUG_LIPSYNC = false
const DEBUG_LIPSYNC_MORPH = true
function debugLog(...args: unknown[]) {
  if (DEBUG_LIPSYNC) console.log('[DEBUG_LIPSYNC]', ...args)
}
function debugMorph(...args: unknown[]) {
  if (DEBUG_LIPSYNC_MORPH) console.log('[LIPSYNC]', ...args)
}

function getBonesMap(model: THREE.Object3D): ReturnType<typeof buildBoneMap> {
  return buildBoneMap(model);
}

export function AvatarRenderer({
  emotion = 'neutral',
  activeViseme,
  isSpeaking = false,
  isListening = false,
  className = '',
}: AvatarRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [modelType, setModelType] = useState<'glb' | 'procedural' | null>(null);
  const sceneRef = useRef<{
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    model: THREE.Object3D | null;
    morphMeshes: THREE.Mesh[];
    bodyAnimator: BodyAnimator | null;
    clock: THREE.Clock;
  } | null>(null);
  const animFrameRef = useRef<number>(0);
  const currentTargetsRef = useRef<Record<string, number>>({});
  const cleanupRef = useRef<(() => void) | null>(null);
  const visemeRef = useRef<VisemeFrame | null | undefined>(null);
  const speakingRef = useRef(isSpeaking)
  const listeningRef = useRef(isListening)
  const emotionRef = useRef(emotion)

  // Sync refs with props without triggering scene rebuild
  speakingRef.current = isSpeaking
  listeningRef.current = isListening
  emotionRef.current = emotion

  const applyBlendShapes = useCallback((targets: Record<string, number>) => {
    currentTargetsRef.current = { ...targets };
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let disposed = false;

    const boot = () => {
      if (disposed) return;
      const width = container.clientWidth;
      const height = container.clientHeight;
      if (width === 0 || height === 0) return;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x1a1a2e);

      const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
      camera.position.set(0, 3, 1.6);
      camera.lookAt(0, 2.6, 0);

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.2;
      container.appendChild(renderer.domElement);

      const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
      scene.add(ambientLight);

      const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
      keyLight.position.set(1, 1.5, 2);
      scene.add(keyLight);

      const fillLight = new THREE.DirectionalLight(0x8888ff, 0.4);
      fillLight.position.set(-1, 0.5, 1);
      scene.add(fillLight);

      const rimLight = new THREE.DirectionalLight(0xffffff, 0.6);
      rimLight.position.set(0, 1, -2);
      scene.add(rimLight);

      const clock = new THREE.Clock();

      const loader = new GLTFLoader();
      loader.load(
        GLB_PATH,
        (gltf) => {
          if (disposed) return;
          const model = gltf.scene;
          centerAndScaleModel(model);
          scene.add(model);

          const morphMeshes: THREE.Mesh[] = [];

          model.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              setupMorphTargets(child);
              if (child.morphTargetInfluences) {
                morphMeshes.push(child);
              }
            }
          });

          const bones = getBonesMap(model);
          const bodyAnimator = new BodyAnimator(bones);

          console.log(`[Avatar] morphMeshes: ${morphMeshes.map(m => m.name).join(', ')}`);
          console.log(`[Avatar] bones: ${Object.keys(bones).join(', ')}`);

          _globalLipSync?.setMeshes(morphMeshes)
          _globalLipSync?.setBodyAnimator(bodyAnimator)
          debugLog('[PIPELINE] meshes set on LipSyncController', morphMeshes.length)

          sceneRef.current = {
            scene, camera, renderer, model, morphMeshes, bodyAnimator, clock,
          };

          setLoading(false);
        },
        undefined,
        () => {
          if (disposed) return;
          const headGroup = buildProceduralHead();
          scene.add(headGroup);

          const morphMeshes: THREE.Mesh[] = [];
          headGroup.traverse((child) => {
            if (child instanceof THREE.Mesh && child.morphTargetDictionary) {
              morphMeshes.push(child);
            }
          });

          const fallbackBones = getBonesMap(headGroup);
          const bodyAnimator = new BodyAnimator(fallbackBones);

          _globalLipSync?.setMeshes(morphMeshes)
          _globalLipSync?.setBodyAnimator(bodyAnimator)
          debugLog('[PIPELINE] meshes set on LipSyncController (procedural)', morphMeshes.length)

          sceneRef.current = {
            scene, camera, renderer, model: headGroup, morphMeshes,
            bodyAnimator, clock,
          };

          setModelType('procedural');
          setLoading(false);
        },
      );

      const animate = () => {
        animFrameRef.current = requestAnimationFrame(animate);
        const s = sceneRef.current;
        if (!s) return;

        const delta = clock.getDelta();
        const targets = { ...currentTargetsRef.current };
        const _isSpeaking = speakingRef.current
        const _isListening = listeningRef.current
        const _emotion = emotionRef.current

        // Determine speaking state from both sources
        const lipSyncSpeaking = _globalLipSync?.isSpeaking ?? false
        const effectiveSpeaking = _isSpeaking || lipSyncSpeaking

        if (effectiveSpeaking !== (window as any).__lastSpeakingState) {
          (window as any).__lastSpeakingState = effectiveSpeaking
          debugMorph('[STATE] speaking:', effectiveSpeaking, 'browser:', _isSpeaking, 'ws:', lipSyncSpeaking)
        }

        // Body animation
        if (s.bodyAnimator) {
          const bodyState: BodyState = effectiveSpeaking ? 'speaking' : _isListening ? 'listening' : _emotion === 'thoughtful' || _emotion === 'considering' ? 'thinking' : 'idle';
          s.bodyAnimator.setState(bodyState);
          const v = visemeRef.current;
          s.bodyAnimator.setViseme(v?.viseme ?? null, v?.weight ?? 0.5);
          s.bodyAnimator.update(delta);

          // Merge body-driven morph targets (blink, body animator lip sync)
          const bodyMorphs = s.bodyAnimator.getMorphTargets();
          Object.assign(targets, bodyMorphs);

          const blink = s.bodyAnimator.getBlinkInfluence();
          if (blink > 0) {
            targets['eyeBlinkLeft'] = blink;
            targets['eyeBlinkRight'] = blink;
          }
        }

        // ELEVENLABS WEBSCKET LIP SYNC — highest priority morph source
        if (_globalLipSync && lipSyncSpeaking) {
          const lipState = _globalLipSync.update(delta)
          const lipMorphs = lipState.morphTargets

          // Override with lip sync targets (highest priority)
          Object.assign(targets, lipMorphs)

          // Log morph target values only when they change significantly
          const jw = lipMorphs['jawOpen']
          const lastJaw = (window as any).__lastJaw
          if (jw !== undefined && (lastJaw === undefined || Math.abs(jw - lastJaw) > 0.05)) {
            (window as any).__lastJaw = jw
            debugMorph('[VISEME]', lipState.currentViseme, 'jawOpen:', jw?.toFixed(2), 'time:', lipState.audioTime?.toFixed(2))
          }
        }

        // Apply morph targets to all meshes
        for (const mesh of s.morphMeshes) {
          if (!mesh.morphTargetInfluences || !mesh.morphTargetDictionary) continue;
          const dict = mesh.morphTargetDictionary as Record<string, number>;
          for (const key of Object.keys(dict)) {
            const idx = dict[key];
            if (idx !== undefined) {
              mesh.morphTargetInfluences[idx] = targets[key] || 0;
            }
          }
        }

        s.renderer.render(s.scene, s.camera);
      };
      animate();

      const handleResize = () => {
        const w = container.clientWidth;
        const h = container.clientHeight;
        if (w === 0 || h === 0) return;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      };
      window.addEventListener('resize', handleResize);

      cleanupRef.current = () => {
        cancelAnimationFrame(animFrameRef.current);
        window.removeEventListener('resize', handleResize);
        renderer.dispose();
        if (container.contains(renderer.domElement)) {
          container.removeChild(renderer.domElement);
        }
        scene.clear();
      };
    };

    boot();

    return () => {
      disposed = true;
      cleanupRef.current?.();
    };
  }, []);

  useEffect(() => {
    visemeRef.current = activeViseme ?? null;
  }, [activeViseme]);

  useEffect(() => {
    if (!isSpeaking) {
      applyBlendShapes({ ...emotionToBlendShapes(emotion), ...silenceBlendShapes() });
    }
  }, [emotion, isSpeaking, applyBlendShapes]);

  // Clean up global lip sync on unmount
  useEffect(() => {
    return () => {
      if (typeof _globalLipSync !== 'undefined' && _globalLipSync) {
        _globalLipSync.destroy();
      }
    };
  }, []);

  useEffect(() => {
    if (activeViseme && isSpeaking) {
      applyBlendShapes({ ...emotionToBlendShapes(emotion), ...visemeToBlendShapes(activeViseme) });
    }
  }, [activeViseme, emotion, isSpeaking, applyBlendShapes]);

  return (
    <div ref={containerRef} className={`relative w-full h-full ${className}`}>
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-overlay rounded-lg z-10">
          <div className="text-center">
            <Loader2 className="animate-spin w-10 h-10 text-action-primary mx-auto mb-2" />
            <p className="text-secondary text-sm">Loading avatar...</p>
          </div>
        </div>
      )}
      {!loading && modelType && (
        <div className="absolute top-2 start-2 z-10">
          <span className="px-2 py-0.5 bg-overlay text-muted text-[10px] rounded-full">
            {modelType === 'glb' ? '3D' : 'Procedural'}
          </span>
        </div>
      )}
    </div>
  );
}
