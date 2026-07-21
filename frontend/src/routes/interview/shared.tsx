import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, ArrowLeft } from 'lucide-react';
import { useInterviewStore } from '../../state/interviewStore';

export function BackButton() {
  const navigate = useNavigate();
  return (
    <div className="absolute top-3 start-3 z-30">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-overlay text-secondary rounded-lg text-xs hover:bg-hover transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>
    </div>
  );
}

export function LoadingScreen({ label = 'Preparing interview...' }: { label?: string }) {
  return (
    <div className="fixed inset-0 bg-page flex items-center justify-center" data-theme="dark">
      <div className="text-center space-y-4">
        <Loader2 className="animate-spin w-12 h-12 text-action-primary mx-auto" />
        <p className="text-secondary">{label}</p>
      </div>
    </div>
  );
}

export function QuestionCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-section/80 backdrop-blur-sm rounded-xl px-5 py-3 border border-default">
      {children}
    </div>
  );
}

export function EvaluationCard({ evaluation, score }: { evaluation: string; score: number }) {
  return (
    <div className="bg-elevated/95 backdrop-blur-sm rounded-xl p-4 border border-default">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-primary text-sm mb-1">Analysis</h4>
          <p className="text-secondary text-sm leading-relaxed">{evaluation}</p>
          {score > 0 && (
            <p className={`mt-1 text-xs font-medium ${score >= 7 ? 'text-success' : score >= 5 ? 'text-warning' : 'text-error'}`}>
              Score: {score}/10
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function QuestionDisplay() {
  const { state } = useInterviewStore();
  if (!state.currentQuestion) return null;

  return state.evaluation ? (
    <EvaluationCard evaluation={state.evaluation.evaluation} score={state.evaluation.score} />
  ) : (
    <QuestionCard>
      <div className="flex items-center gap-2 mb-1">
        <span className="px-2 py-0.5 bg-action-primary text-inverse text-[10px] rounded-full font-medium">
          Q{state.currentQuestion.question_number}
        </span>
        {state.session?.current_phase && (
          <span className="px-2 py-0.5 bg-action-primary/80 text-inverse text-[10px] rounded-full capitalize">
            {state.session.current_phase}
          </span>
        )}
      </div>
      <p className="text-primary text-sm leading-relaxed">
        {state.currentQuestion.question}
      </p>
    </QuestionCard>
  );
}

interface InputBarProps {
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  isSending: boolean;
  placeholder?: string;
  children?: React.ReactNode;
  statusIndicator?: React.ReactNode;
}

export function InputBar({ input, onInputChange, onSend, onKeyDown, isSending, placeholder = 'Type your answer here...', children, statusIndicator }: InputBarProps) {
  const { state } = useInterviewStore();

  return (
    <div className="bg-section border-t border-default p-3 z-30">
      <div className="max-w-2xl mx-auto flex gap-3 items-end">
        {children}
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
            rows={2}
            disabled={isSending}
            className="w-full px-4 py-2.5 bg-input text-primary border border-strong rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus disabled:bg-input transition-all text-sm placeholder-muted"
          />
        </div>
        <button
          onClick={onSend}
          disabled={!input.trim() || isSending || !state.currentQuestion}
          className="w-11 h-11 bg-action-primary text-inverse rounded-full flex items-center justify-center hover:bg-action-primary-hover disabled:opacity-30 disabled:cursor-not-allowed transition-all shrink-0">
          {isSending ? <Loader2 className="animate-spin w-5 h-5" /> : <span className="w-5 h-5 flex items-center justify-center">&#10148;</span>}
        </button>
      </div>
      {statusIndicator && (
        <div className="max-w-2xl mx-auto flex items-center gap-3 mt-2 text-xs text-muted">
          {statusIndicator}
        </div>
      )}
    </div>
  );
}
