import React from 'react';
import { Mic, MicOff } from 'lucide-react';
import { useInterviewStore } from '../../state/interviewStore';
import { useVoice } from '../../hooks/useVoice';
import { useCamera } from '../../hooks/useCamera';
import { AvatarRenderer, getLipSyncController } from '../../components/AvatarRenderer';
import { CameraPreview } from '../../components/CameraPreview';
import type { AvatarEmotion } from '../../types/avatar';
import { BackButton, LoadingScreen, QuestionDisplay, InputBar } from './shared';

export function AvatarMode() {
  const { state, actions } = useInterviewStore();
  const voice = useVoice();
  const camera = useCamera();
  const [input, setInput] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);
  const [avatarEmotion, setAvatarEmotion] = React.useState<AvatarEmotion>('neutral');

  React.useEffect(() => {
    camera.startCamera();
    return () => camera.stopCamera();
  }, []);

  React.useEffect(() => {
    if (state.session?.session_id) {
      getLipSyncController()?.connect(state.session.session_id, 'localhost:8000');
    }
    return () => {
      getLipSyncController()?.disconnect();
    };
  }, [state.session?.session_id]);

  React.useEffect(() => {
    if (state.session && state.currentQuestion?.question) {
      const t = setTimeout(() => {
        getLipSyncController()?.speak(state.currentQuestion!.question);
      }, 600);
      return () => clearTimeout(t);
    }
  }, [state.session?.session_id]);

  const [lcSpeaking, setLcSpeaking] = React.useState(false);
  React.useEffect(() => {
    const id = setInterval(() => {
      setLcSpeaking(getLipSyncController()?.isSpeaking ?? false);
    }, 100);
    return () => clearInterval(id);
  }, []);

  const effectiveIsSpeaking = voice.isSpeaking || lcSpeaking;

  React.useEffect(() => {
    if (effectiveIsSpeaking) {
      setAvatarEmotion('excited');
    } else if (voice.isListening) {
      setAvatarEmotion('considering');
    } else {
      setAvatarEmotion('neutral');
    }
  }, [effectiveIsSpeaking, voice.isListening]);

  React.useEffect(() => {
    if (voice.transcript) {
      setInput(voice.transcript);
    }
  }, [voice.transcript]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !state.currentQuestion || isSending) return;
    setIsSending(true);
    voice.stopVoice();
    try {
      await actions.submitAnswer(text);
      setInput('');
      voice.resetTranscript();
      if (state.currentQuestion?.question) {
        getLipSyncController()?.speak(state.currentQuestion.question);
      }
    } catch {
    } finally {
      setIsSending(false);
    }
  };

  const handleMicToggle = () => {
    if (voice.isListening) {
      voice.stopVoice();
    } else {
      voice.startVoice();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!state.currentQuestion) {
    return <LoadingScreen label="Preparing avatar interview..." />;
  }

  return (
    <div className="flex-1 h-full bg-page flex flex-col" data-theme="dark">
      <BackButton />

      <div className="relative flex-1 min-h-0">
        <AvatarRenderer
          emotion={avatarEmotion}
          activeViseme={null}
          isSpeaking={effectiveIsSpeaking}
          isListening={voice.isListening}
          className="w-full h-full"
        />

        <div className="absolute top-4 right-4 z-20">
          <CameraPreview
            stream={camera.stream}
            isCameraOn={camera.isCameraOn}
            onToggle={camera.isCameraOn ? camera.stopCamera : camera.startCamera}
            size="sm"
          />
        </div>

        <div className="absolute bottom-0 inset-x-0 z-20 p-4">
          <div className="max-w-2xl mx-auto">
            <QuestionDisplay />
          </div>
        </div>
      </div>

      <InputBar
        input={voice.interimText || input}
        onInputChange={setInput}
        onSend={handleSend}
        onKeyDown={handleKeyDown}
        isSending={isSending}
        placeholder={voice.isListening ? 'Listening...' : 'Type your answer...'}
        statusIndicator={
          <>
            {voice.isListening && (
              <span className="flex items-center gap-1 text-success">
                <span className="w-1.5 h-1.5 bg-success rounded-full animate-pulse" /> Recording...
              </span>
            )}
            {effectiveIsSpeaking && (
              <span className="flex items-center gap-1 text-action-primary">
                <span className="w-1.5 h-1.5 bg-action-primary rounded-full animate-pulse" /> Speaking...
              </span>
            )}
            {!voice.isSupported && <span className="text-warning">Voice not supported</span>}
          </>
        }
      >
        <button
          onClick={handleMicToggle}
          disabled={isSending || !voice.isSupported}
          className={`w-11 h-11 rounded-full flex items-center justify-center transition-all shrink-0 ${
            voice.isListening
              ? 'bg-error text-inverse animate-pulse'
              : 'bg-input text-muted hover:bg-hover'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {voice.isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>
      </InputBar>
    </div>
  );
}
