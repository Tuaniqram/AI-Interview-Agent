import type { SpeakingSpeed } from './avatar';

export interface VisemeFrame {
  viseme: string;
  timestamp: number;
  weight: number;
}

export interface TranscriptEvent {
  text: string;
  isFinal: boolean;
  timestamp: number;
}

export interface VoiceState {
  isListening: boolean;
  isSpeaking: boolean;
  isSupported: boolean;
  transcript: string;
  interimText: string;
  error: string | null;
  activeViseme: VisemeFrame | null;
}

export interface TTSOptions {
  text: string;
  speed?: SpeakingSpeed;
  onViseme?: (viseme: VisemeFrame) => void;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (error: string) => void;
}
