import { useState, useCallback, useRef, useEffect } from 'react';
import { voiceService } from '../services/voiceService';
import type { VoiceState, VisemeFrame } from '../types/voice';

export function useVoice() {
  const [state, setState] = useState<VoiceState>({
    isListening: false,
    isSpeaking: false,
    isSupported: voiceService.isSupported,
    transcript: '',
    interimText: '',
    error: null,
    activeViseme: null,
  });
  const finalTranscriptRef = useRef('');

  useEffect(() => {
    voiceService.stopListening();
    voiceService.stopSpeaking();
    return () => {
      voiceService.stopListening();
      voiceService.stopSpeaking();
    };
  }, []);

  const startVoice = useCallback(() => {
    setState(prev => ({ ...prev, error: null, interimText: '', isListening: true }));
    finalTranscriptRef.current = state.transcript;

    voiceService.startListening({
      onTranscript: (text, isFinal) => {
        if (isFinal) {
          finalTranscriptRef.current += (finalTranscriptRef.current ? ' ' : '') + text;
          setState(prev => ({
            ...prev,
            transcript: finalTranscriptRef.current,
            interimText: '',
            isListening: true,
          }));
        } else {
          setState(prev => ({
            ...prev,
            interimText: text,
            isListening: true,
          }));
        }
      },
      onError: (error) => {
        setState(prev => ({ ...prev, error, isListening: false }));
      },
    });
  }, [state.transcript]);

  const stopVoice = useCallback(() => {
    if (!voiceService.isMicActive) return;
    voiceService.stopListening();
    setState(prev => ({ ...prev, isListening: false, interimText: '' }));
  }, []);

  const speakText = useCallback((text: string) => {
    return new Promise<void>((resolve) => {
      voiceService.speak({
        text,
        speed: 'normal',
        onStart: () => setState(prev => ({ ...prev, isSpeaking: true })),
        onViseme: (viseme: VisemeFrame) => {
          setState(prev => ({ ...prev, activeViseme: viseme }));
        },
        onEnd: () => {
          setState(prev => ({ ...prev, isSpeaking: false, activeViseme: null }));
          resolve();
        },
        onError: (error) => {
          setState(prev => ({ ...prev, error, isSpeaking: false, activeViseme: null }));
          resolve();
        },
      });
    });
  }, []);

  const stopSpeaking = useCallback(() => {
    voiceService.stopSpeaking();
    setState(prev => ({ ...prev, isSpeaking: false, activeViseme: null }));
  }, []);

  const resetTranscript = useCallback(() => {
    finalTranscriptRef.current = '';
    setState(prev => ({ ...prev, transcript: '', interimText: '' }));
  }, []);

  return {
    ...state,
    startVoice,
    stopVoice,
    speakText,
    stopSpeaking,
    resetTranscript,
  };
}
