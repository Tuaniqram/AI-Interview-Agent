import React from 'react';
import { useInterviewStore } from '../state/interviewStore';
import { Loader2, Send, RotateCcw, Lightbulb } from 'lucide-react';

type InterviewMode = 'typing' | 'voice' | 'avatar' | 'realtime';

export function InterviewLayout({ mode = 'typing' }: { mode?: InterviewMode }) {
  const { state, actions } = useInterviewStore();
  const [isSending, setIsSending] = React.useState(false);
  const [input, setInput] = React.useState('');
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const handlePressEnter = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isSending && state.currentQuestion) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !state.currentQuestion || isSending) return;

    setIsSending(true);
    try {
      await actions.submitAnswer(input);
      setInput('');
      textareaRef.current?.focus();
    } catch {
      // Error handled by store
    } finally {
      setIsSending(false);
    }
  };

  if (!state.currentQuestion) {
    return (
      <div className="min-h-[400px] bg-elevated rounded-xl p-8 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="animate-spin w-12 h-12 text-action-primary mx-auto" />
          <p className="text-secondary text-sm">Preparing interview...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[500px] bg-elevated rounded-xl flex flex-col">
      {/* Question Area */}
        <div className="p-6 flex-1">
        <div className="mb-4">
          <span className="inline-block px-3 py-1 bg-action-primary/15 text-action-primary rounded-full text-xs font-medium">
            Question {state.currentQuestion.question_number || 0}
          </span>
        </div>
        <h2 className="text-xl font-semibold text-primary leading-relaxed">
          {state.currentQuestion.question}
        </h2>
      </div>

      {/* Previous Answer Display */}
      {state.userAnswer && (
        <div className="px-6 py-4 bg-section">
          <div className="flex items-start gap-3">
            <span className="text-sm font-medium text-secondary mt-0.5">Your Answer:</span>
            <p className="text-primary text-sm flex-1">{state.userAnswer}</p>
          </div>
        </div>
      )}

      {/* Answer Area */}
        <div className="p-6 flex-1">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handlePressEnter}
          placeholder={mode === 'voice'
            ? 'Transcribed answer will appear here...'
            : 'Type your answer here...'}
          disabled={!state.currentQuestion || isSending}
          rows={6}
          className="w-full px-4 py-3 bg-input text-primary rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] disabled:bg-hover disabled:text-muted transition-all text-sm placeholder-muted"
        />
      </div>

      {/* Actions */}
      <div className="p-6 bg-section">
        <div className="flex justify-between items-center">
          <button
            onClick={() => setInput('')}
            disabled={isSending || !input}
            className="px-5 py-2 text-sm font-medium rounded-lg text-action-ghost-text hover:bg-action-ghost-hover disabled:bg-action-disabled disabled:text-action-disabled-text disabled:cursor-not-allowed transition-colors"
          >
            <span className="inline-flex items-center gap-2">
              <RotateCcw className="w-3.5 h-3.5" />
              Clear
            </span>
          </button>
          <button
            onClick={handleSend}
            disabled={!state.currentQuestion || isSending || !input.trim()}
            className="px-6 py-2 text-sm font-medium bg-action-primary text-inverse rounded-lg hover:bg-action-primary-hover active:scale-[0.98] disabled:bg-action-disabled disabled:text-action-disabled-text disabled:cursor-not-allowed transition-all inline-flex items-center gap-2"
          >
            {isSending ? (
              <>
                <Loader2 className="animate-spin w-4 h-4" />
                Evaluating...
              </>
            ) : (
              <>
                Evaluate & Next
                <Send className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Feedback / Analysis Area */}
      {state.evaluation && (
        <div className="p-6">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-full bg-action-primary/15 shrink-0">
              <Lightbulb className="w-5 h-5 text-action-primary" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-primary text-sm mb-2">Analysis</h4>
              <p className="text-secondary text-sm leading-relaxed">{state.evaluation.evaluation}</p>
              {state.evaluation.score > 0 && (
                <p className="mt-2 text-xs font-medium text-action-primary">
                  Score: {state.evaluation.score}/10
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
