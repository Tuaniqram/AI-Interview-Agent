import React from 'react';
import { Loader2, Mic, MicOff, Send } from 'lucide-react';
import { useInterviewStore } from '../state/interviewStore';
import { useVoice } from '../hooks/useVoice';
import { useCamera } from '../hooks/useCamera';
import { AvatarRenderer, getLipSyncController } from './AvatarRenderer';
import { CameraPreview } from './CameraPreview';
import type { AvatarEmotion } from '../types/avatar';

export function AvatarLayout() {
  const { state, actions } = useInterviewStore();
  const voice = useVoice();
  const camera = useCamera();

  const [input, setInput] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);
  const [avatarEmotion, setAvatarEmotion] = React.useState<AvatarEmotion>('neutral');

  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    camera.startCamera();
    return () => camera.stopCamera();
  }, []);

  // Connect WebSocket for lip-sync when session starts
  React.useEffect(() => {
    if (state.session?.session_id) {
      getLipSyncController()?.connect(state.session.session_id, 'localhost:8000');
    }
    return () => {
      getLipSyncController()?.disconnect();
    };
  }, [state.session?.session_id]);

  // Speak the first question when session starts
  React.useEffect(() => {
    if (state.session && state.currentQuestion?.question) {
      const t = setTimeout(() => {
        getLipSyncController()?.speak(state.currentQuestion!.question);
      }, 600);
      return () => clearTimeout(t);
    }
  }, [state.session?.session_id]);

  // Track lip-sync speaking state for emotion/UI
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
    return (
      <div className="fixed inset-0 bg-gray-900 flex items-center justify-center z-50">
        <div className="text-center space-y-4">
          <Loader2 className="animate-spin w-12 h-12 text-purple-400 mx-auto" />
          <p className="text-gray-300">Preparing avatar interview...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-gray-900 flex flex-col">
      {/* Full-screen Avatar */}
      <div className="relative flex-1 min-h-0">
        <AvatarRenderer
          emotion={avatarEmotion}
          activeViseme={voice.activeViseme}
          isSpeaking={effectiveIsSpeaking}
          isListening={voice.isListening}
          className="w-full h-full"
        />

        {/* Camera Preview - PiP top-right */}
        <div className="absolute top-4 right-4 z-20">
          <CameraPreview
            stream={camera.stream}
            isCameraOn={camera.isCameraOn}
            onToggle={camera.isCameraOn ? camera.stopCamera : camera.startCamera}
            size="sm"
          />
        </div>

        {/* Bug 2 fix: Evaluation or Question overlay, never both */}
        {state.evaluation ? (
          <div className="absolute bottom-0 left-0 right-0 z-20 p-4">
            <div className="max-w-2xl mx-auto bg-gray-800/95 backdrop-blur-sm rounded-xl p-4 border border-gray-700">
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-white text-sm mb-1">Analysis</h4>
                  <p className="text-gray-300 text-sm leading-relaxed">{state.evaluation.evaluation}</p>
                  {state.evaluation.score > 0 && (
                    <p className="mt-1 text-xs font-medium text-purple-400">
                      Score: {state.evaluation.score}/10
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="absolute bottom-0 left-0 right-0 z-20 p-4">
            <div className="max-w-2xl mx-auto">
              <div className="bg-black/60 backdrop-blur-sm rounded-xl px-5 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 bg-purple-600 text-white text-[10px] rounded-full font-medium">
                    Q{state.currentQuestion.question_number}
                  </span>
                  {state.session?.current_phase && (
                    <span className="px-2 py-0.5 bg-indigo-600 text-white text-[10px] rounded-full capitalize">
                      {state.session.current_phase}
                    </span>
                  )}
                </div>
                <p className="text-white text-sm leading-relaxed">
                  {state.currentQuestion.question}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Bar - bottom */}
      <div className="bg-gray-900 border-t border-gray-800 p-3 z-30">
        <div className="max-w-2xl mx-auto flex gap-3 items-end">
          {/* Mic Button */}
          <button
            onClick={handleMicToggle}
            disabled={isSending || !voice.isSupported}
            className={`w-11 h-11 rounded-full flex items-center justify-center transition-all shrink-0 ${
              voice.isListening
                ? 'bg-red-500 text-white animate-pulse'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {voice.isListening ? (
              <MicOff className="w-5 h-5" />
            ) : (
              <Mic className="w-5 h-5" />
            )}
          </button>

          {/* Text Input */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={voice.interimText || input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={voice.isListening ? 'Listening...' : 'Type your answer...'}
              rows={1}
              disabled={isSending}
              className="w-full px-4 py-2.5 bg-gray-800 text-white border border-gray-700 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-800 transition-all text-sm placeholder-gray-500"
            />
            {voice.error && (
              <p className="text-red-400 text-xs mt-1">{voice.error}</p>
            )}
          </div>

          {/* Send Button */}
          <button
            onClick={handleSend}
            disabled={!input.trim() || isSending || !state.currentQuestion}
            className="w-11 h-11 bg-purple-600 text-white rounded-full flex items-center justify-center hover:bg-purple-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all shrink-0"
          >
            {isSending ? (
              <Loader2 className="animate-spin w-5 h-5" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Voice Status */}
        <div className="max-w-2xl mx-auto flex items-center gap-3 mt-2 text-[11px] text-gray-500">
          {voice.isListening && (
            <span className="flex items-center gap-1 text-green-500">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              Recording...
            </span>
          )}
          {effectiveIsSpeaking && (
            <span className="flex items-center gap-1 text-purple-400">
              <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse" />
              Speaking...
            </span>
          )}
          {!voice.isSupported && (
            <span className="text-yellow-500">Voice not supported</span>
          )}
        </div>
      </div>
    </div>
  );
}