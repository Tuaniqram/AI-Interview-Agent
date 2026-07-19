import React from 'react';
import { useInterviewStore } from '../state/interviewStore';
import { Loader2 } from 'lucide-react';

type InterviewMode = 'typing' | 'voice' | 'avatar' | 'realtime';

/**
 * Interview Layout Component
 * Renders the main interview interface with question progression and feedback
 */
export function InterviewLayout({ mode = 'typing' }: { mode?: InterviewMode }) {
  const { state, actions } = useInterviewStore();
  const [isSending, setIsSending] = React.useState(false);
  const [input, setInput] = React.useState('');
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  // Source type for answer submission (exclude 'realtime' since it's not yet implemented)
  const source: 'typing' | 'voice' | 'avatar' = (mode === 'realtime' ? 'typing' : mode);

  const handlePressEnter = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isSending && state.currentQuestion) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !state.currentQuestion || isSending) return;

    console.log('[InterviewLayout] Submitting answer:', { answer: input, source, questionNumber: state.currentQuestion.question_number });
    setIsSending(true);
    try {
      await actions.submitAnswer(input);
      setInput('');
      textareaRef.current?.focus();
    } catch (error) {
      // Error handled by store
      console.error('Failed to send answer:', error);
    } finally {
      setIsSending(false);
    }
  };

  // Debug: log current render state (temporary audit trace)
  console.log('[InterviewLayout] render state:', {
    sessionId: state.session?.session_id,
    currentQuestion: state.currentQuestion?.question_number,
    questionNumber: state.currentQuestion?.question_number,
    answer: input,
    isLoading: state.isLoading,
    isEvaluating: state.isEvaluating,
    evaluation: state.evaluation,
  });

  // If no current question, show loading or wait for one
  if (!state.currentQuestion) {
    return (
      <div className="min-h-[400px] bg-white rounded-2xl shadow-lg p-8 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="animate-spin w-12 h-12 text-purple-600 mx-auto" />
          <p className="text-gray-700">Preparing interview...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[500px] bg-white rounded-2xl shadow-lg flex flex-col">
      {/* Question Area */}
      <div className="p-6 border-b border-gray-100 flex-1">
        <div className="mb-4">
          <span className="inline-block px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
            Question {state.currentQuestion?.question_number || 0}
          </span>
        </div>
        <h2 className="text-xl font-semibold text-gray-800 leading-relaxed">
          {state.currentQuestion?.question}
        </h2>
      </div>

      {/* Previous Answer Display */}
      {state.userAnswer && (
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-100">
          <div className="flex items-start gap-3">
            <span className="text-lg">💬</span>
            <div>
              <span className="text-sm font-medium text-gray-600">Your Answer:</span>
              <p className="text-gray-800 mt-1 text-sm">{state.userAnswer}</p>
            </div>
          </div>
        </div>
      )}

      {/* Answer Area */}
      <div className="p-6 border-b border-gray-100 flex-1">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handlePressEnter}
          placeholder={mode === 'voice' 
            ? 'Transcribed answer will appear here...' 
            : 'Type your answer here...'}
          disabled={!state.currentQuestion || isSending}
          rows={6}
          className="w-full px-4 py-3 border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-400 transition-all"
        />
      </div>

      {/* Actions */}
      <div className="p-6 bg-gray-50">
        <div className="flex justify-between items-center">
          <button
            onClick={() => setInput('')}
            disabled={isSending || !input}
            className="px-6 py-2.5 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            Clear
          </button>
          <button
            onClick={() => {
              console.log('[InterviewLayout] SUBMIT ANSWER clicked', {
                answer: input,
                questionNumber: state.currentQuestion?.question_number,
              });
              handleSend();
            }}
            disabled={!state.currentQuestion || isSending || !input.trim()}
            className="px-8 py-2.5 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
          >
            {isSending ? (
              <>
                <Loader2 className="animate-spin w-4 h-4" />
                Evaluating...
              </>
            ) : (
              <>
                Evaluate & Next
                {mode !== 'typing' && (
                  <span className="text-sm opacity-80">
                    ({mode === 'voice' ? '🎤' : mode === 'avatar' ? '🎭' : '💬'})
                  </span>
                )}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Feedback / Analysis Area */}
      {state.evaluation && (
        <div className="p-6 bg-gradient-to-r from-purple-50 to-indigo-50">
          <div className="flex items-start gap-3">
            <div className="text-2xl">💡</div>
            <div className="flex-1">
              <h4 className="font-semibold text-gray-800 mb-2">Analysis</h4>
              <p className="text-gray-700 leading-relaxed">{state.evaluation.evaluation}</p>
              {state.evaluation.score && (
                <p className="mt-2 text-sm">Score: {state.evaluation.score}/10</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}