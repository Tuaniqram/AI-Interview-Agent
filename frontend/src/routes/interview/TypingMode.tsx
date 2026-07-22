import React from 'react';
import { useInterviewStore } from '../../state/interviewStore';
import { LoadingScreen, ConversationThread, InputBar } from './shared';

export function TypingMode() {
  const { state, actions } = useInterviewStore();
  const [input, setInput] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !state.currentQuestion || isSending) return;
    setIsSending(true);
    try {
      await actions.submitAnswer(text);
      setInput('');
    } catch {
    } finally {
      setIsSending(false);
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
    <div className="flex-1 h-full bg-page flex flex-col min-h-0" data-theme="dark">
      <ConversationThread />

      <InputBar
        input={input}
        onInputChange={setInput}
        onSend={handleSend}
        onKeyDown={handleKeyDown}
        isSending={isSending}
        placeholder="Type your answer..."
      />
    </div>
  );
}
