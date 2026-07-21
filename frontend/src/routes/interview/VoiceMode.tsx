import React from 'react';
import { Mic, MicOff } from 'lucide-react';
import { useInterviewStore } from '../../state/interviewStore';
import { useVoice } from '../../hooks/useVoice';
import { BackButton, LoadingScreen, QuestionDisplay, InputBar } from './shared';

export function VoiceMode() {
  const { state, actions } = useInterviewStore();
  const voice = useVoice();
  const [input, setInput] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);

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
    return <LoadingScreen />;
  }

  return (
    <div className="fixed inset-0 bg-page flex flex-col" data-theme="dark">
      <BackButton />

      <div className="flex-1 flex flex-col items-center justify-center p-6 min-h-0">
        <div className="w-full max-w-2xl space-y-4">
          <QuestionDisplay />
        </div>
      </div>

      <InputBar
        input={voice.interimText || input}
        onInputChange={setInput}
        onSend={handleSend}
        onKeyDown={handleKeyDown}
        isSending={isSending}
        placeholder={voice.isListening ? 'Listening...' : 'Type or speak your answer...'}
        statusIndicator={
          <>
            {voice.isListening && (
              <span className="flex items-center gap-1 text-success">
                <span className="w-1.5 h-1.5 bg-success rounded-full animate-pulse" /> Recording...
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
          } disabled:opacity-50 disabled:cursor-not-allowed`}>
          {voice.isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>
      </InputBar>
    </div>
  );
}
