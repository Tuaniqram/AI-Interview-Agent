import type { VisemeFrame, TTSOptions } from '../types/voice';

type SpeechRecognitionInstance = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: { resultIndex: number; results: SpeechRecognitionResult[] }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

function getSpeechRecognition(): SpeechRecognitionInstance | null {
  const Ctor = (window as unknown as Record<string, unknown>).SpeechRecognition ||
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition;
  return Ctor ? new (Ctor as new () => SpeechRecognitionInstance)() : null;
}

class VoiceService {
  private recognition: SpeechRecognitionInstance | null = null;
  private isListening = false;
  private pendingStart: (() => void) | null = null;
  private onTranscriptCallback: ((text: string, isFinal: boolean) => void) | null = null;
  private onErrorCallback: ((error: string) => void) | null = null;
  private synth: SpeechSynthesis | null = null;
  private preferredVoice: SpeechSynthesisVoice | null = null;

  constructor() {
    this.recognition = getSpeechRecognition();
    this.synth = window.speechSynthesis || null;
    this.loadVoice();
  }

  private loadVoice() {
    if (!this.synth) return;
    const trySelect = () => {
      const voices = this.synth!.getVoices();
      if (voices.length === 0) return false;
      // Preference order: mature, natural voices
      const preferred = [
        'Microsoft David', 'Google UK English Female', 'Google US English',
        'Samantha', 'Alex', 'Microsoft Zira',
      ];
      for (const name of preferred) {
        const v = voices.find(v => v.name.includes(name));
        if (v) { this.preferredVoice = v; return true; }
      }
      // Fallback: any English voice
      const en = voices.find(v => v.lang.startsWith('en'));
      if (en) { this.preferredVoice = en; return true; }
      // Last resort: first available
      this.preferredVoice = voices[0];
      return true;
    };
    if (!trySelect()) {
      this.synth.onvoiceschanged = () => trySelect();
    }
  }

  get isSupported(): boolean {
    return this.recognition !== null;
  }

  get isMicActive(): boolean {
    return this.isListening;
  }

  startListening(params: {
    onTranscript: (text: string, isFinal: boolean) => void;
    onError?: (error: string) => void;
  }): void {
    if (!this.recognition) {
      params.onError?.('Speech recognition not supported in this browser');
      return;
    }

    this.onTranscriptCallback = params.onTranscript;
    this.onErrorCallback = params.onError ?? null;

    const doStart = () => {
      if (!this.recognition) return;

      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = 'en-US';

      this.recognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const text = result[0].transcript;
          const isFinal = result.isFinal;
          this.onTranscriptCallback?.(text, isFinal);
        }
      };

      this.recognition.onerror = (event) => {
        this.onErrorCallback?.(event.error);
        this.isListening = false;
      };

      this.recognition.onend = () => {
        this.isListening = false;
        if (this.pendingStart) {
          const next = this.pendingStart;
          this.pendingStart = null;
          next();
        }
      };

      try {
        this.recognition.start();
        this.isListening = true;
      } catch {
        this.isListening = false;
      }
    };

    this.pendingStart = null;

    if (this.isListening && this.recognition) {
      this.recognition.onend = () => {
        this.isListening = false;
        doStart();
      };
      try {
        this.recognition.stop();
      } catch {
        doStart();
      }
    } else {
      doStart();
    }
  }

  stopListening(): void {
    this.pendingStart = null;
    if (!this.recognition || !this.isListening) return;
    try {
      this.recognition.stop();
    } catch {
      // ignore if already stopped
    }
    this.isListening = false;
  }

  speak(options: TTSOptions): void {
    if (!this.synth) {
      options.onError?.('Speech synthesis not supported');
      return;
    }

    this.synth.cancel();

    const utterance = new SpeechSynthesisUtterance(options.text);
    // Professional interview pace: calm and deliberate
    utterance.rate = options.speed === 'slow' ? 0.85 : options.speed === 'fast' ? 1.05 : 0.92;
    utterance.pitch = 1.0;
    utterance.volume = 1;
    if (this.preferredVoice) {
      utterance.voice = this.preferredVoice;
    }

    utterance.onstart = () => options.onStart?.();
    utterance.onend = () => options.onEnd?.();
    utterance.onerror = (event) => options.onError?.(event.error);

    utterance.onboundary = (event) => {
      if (event.name === 'word' && options.onViseme) {
        const visemeFrame: VisemeFrame = {
          viseme: mapCharToViseme(event.utterance.text[event.charIndex] || ' '),
          timestamp: event.charIndex,
          weight: 0.8,
        };
        options.onViseme(visemeFrame);
      }
    };

    this.synth.speak(utterance);
  }

  stopSpeaking(): void {
    this.synth?.cancel();
  }
}

function mapCharToViseme(char: string): string {
  const map: Record<string, string> = {
    'a': 'AA', 'e': 'AE', 'i': 'IH', 'o': 'OH', 'u': 'UW',
    'b': 'B', 'p': 'B', 'm': 'M', 'f': 'F', 'v': 'F',
    't': 'T', 'd': 'T', 's': 'SS', 'z': 'SS',
    'k': 'K', 'g': 'K', 'n': 'N', 'l': 'L',
    'r': 'R', 'w': 'W',
  };
  return map[char.toLowerCase()] || 'sil';
}

export const voiceService = new VoiceService();
