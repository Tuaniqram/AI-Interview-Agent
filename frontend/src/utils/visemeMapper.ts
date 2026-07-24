import type { VisemeFrame } from '../types/voice';
import type { AvatarEmotion } from '../types/avatar';

export interface BlendShapeWeights {
  [morphTarget: string]: number;
}

// Map ARPABET/phoneme viseme codes to the model's 15 viseme morph targets.
// The model has Blender viseme shape keys: CH, DD, E, FF, PP, RR, SS, TH, aa, ih, kk, nn, oh, ou, sil.
const PHONEME_TO_VISEME: Record<string, Record<string, number>> = {
  // Silence / neutral
  'sil': { sil: 1.0 },

  // Vowels — direct viseme matches
  'AA': { aa: 1.0 },
  'AE': { E: 0.5, aa: 0.5 },
  'AH': { aa: 0.7, ih: 0.3 },
  'AO': { aa: 0.4, oh: 0.6 },
  'AW': { aa: 0.5, ou: 0.5 },
  'AY': { aa: 0.6, ih: 0.4 },
  'EH': { E: 1.0 },
  'ER': { RR: 0.6, E: 0.4 },
  'EY': { E: 0.7, ih: 0.3 },
  'IH': { ih: 1.0 },
  'IY': { ih: 0.7, E: 0.3 },
  'OH': { oh: 1.0 },
  'OW': { oh: 0.7, ou: 0.3 },
  'OY': { oh: 0.5, ih: 0.5 },
  'UH': { ou: 0.7, ih: 0.3 },
  'UW': { ou: 1.0 },

  // Consonants — direct viseme matches
  'CH': { CH: 1.0 },
  'DD': { DD: 1.0 },
  'DH': { DD: 0.6, TH: 0.4 },
  'E': { E: 1.0 },
  'F': { FF: 1.0 },
  'FF': { FF: 1.0 },
  'KK': { kk: 1.0 },
  'NN': { nn: 1.0 },
  'PP': { PP: 1.0 },
  'RR': { RR: 1.0 },
  'SS': { SS: 1.0 },
  'TH': { TH: 1.0 },
  'aa': { aa: 1.0 },
  'ih': { ih: 1.0 },
  'kk': { kk: 1.0 },
  'nn': { nn: 1.0 },
  'oh': { oh: 1.0 },
  'ou': { ou: 1.0 },

  // Secondary mappings (no direct viseme match, use nearest)
  'B': { PP: 0.9, DD: 0.1 },
  'D': { DD: 0.8, TH: 0.2 },
  'G': { kk: 0.8, DD: 0.2 },
  'JH': { CH: 0.7, DD: 0.3 },
  'K': { kk: 1.0 },
  'L': { RR: 0.4, DD: 0.4, nn: 0.2 },
  'M': { PP: 0.8, nn: 0.2 },
  'N': { nn: 1.0 },
  'NG': { nn: 0.6, kk: 0.4 },
  'P': { PP: 1.0 },
  'R': { RR: 0.8, DD: 0.2 },
  'S': { SS: 1.0 },
  'SH': { CH: 1.0 },
  'T': { DD: 0.7, TH: 0.3 },
  'V': { FF: 0.8, DD: 0.2 },
  'W': { ou: 0.6, RR: 0.4 },
  'Y': { ih: 0.5, E: 0.5 },
  'Z': { SS: 0.7, DD: 0.3 },
  'ZH': { CH: 0.6, SS: 0.4 },
};

// Emotion → ARKit blendshape combinations
const CUSTOM_EMOTION_MAP: Record<AvatarEmotion, Record<string, number>> = {
  neutral: {},
  laughing: {
    mouthSmileLeft: 0.7, mouthSmileRight: 0.7,
    cheekSquintLeft: 0.5, cheekSquintRight: 0.5,
    jawOpen: 0.3,
    eyeBlinkLeft: 0.2, eyeBlinkRight: 0.2,
  },
  considering: {
    browDownLeft: 0.4, browDownRight: 0.4,
    eyeSquintLeft: 0.2, eyeSquintRight: 0.2,
    mouthPressLeft: 0.15, mouthPressRight: 0.15,
  },
  excited: {
    browInnerUp: 0.6,
    eyeWideLeft: 0.4, eyeWideRight: 0.4,
    mouthSmileLeft: 0.6, mouthSmileRight: 0.6,
    jawOpen: 0.2,
  },
  thoughtful: {
    browDownLeft: 0.3, browDownRight: 0.1,
    eyeLookUpLeft: 0.3, eyeLookUpRight: 0.3,
    mouthStretchLeft: 0.1, mouthStretchRight: 0.1,
    mouthPressLeft: 0.1, mouthPressRight: 0.1,
  },
  happy: {
    mouthSmileLeft: 0.8, mouthSmileRight: 0.8,
    cheekSquintLeft: 0.4, cheekSquintRight: 0.4,
  },
  concerned: {
    browDownLeft: 0.5, browDownRight: 0.5,
    browInnerUp: 0.2,
    eyeSquintLeft: 0.3, eyeSquintRight: 0.3,
    mouthFrownLeft: 0.3, mouthFrownRight: 0.3,
  },
  confident: {
    browInnerUp: 0.2,
    eyeWideLeft: 0.3, eyeWideRight: 0.3,
    mouthSmileLeft: 0.5, mouthSmileRight: 0.5,
    jawOpen: 0.1,
  },
  surprised: {
    browInnerUp: 0.8, browDownLeft: 0.2, browDownRight: 0.2,
    eyeWideLeft: 0.8, eyeWideRight: 0.8,
    jawOpen: 0.6,
    mouthStretchLeft: 0.3, mouthStretchRight: 0.3,
  },
};

export function visemeToBlendShapes(viseme: VisemeFrame): BlendShapeWeights {
  const targets = PHONEME_TO_VISEME[viseme.viseme] || {};
  const result: BlendShapeWeights = {};
  for (const [key, base] of Object.entries(targets)) {
    result[key] = base * viseme.weight;
  }
  return result;
}

export function emotionToBlendShapes(emotion: AvatarEmotion): BlendShapeWeights {
  return { ...CUSTOM_EMOTION_MAP[emotion] };
}

export function silenceBlendShapes(): BlendShapeWeights {
  return {};
}
