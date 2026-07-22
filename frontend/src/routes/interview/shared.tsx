import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, ArrowLeft, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { useInterviewStore } from '../../state/interviewStore';

const PHASES = ['intro', 'experience', 'technical', 'behavioral', 'conclusion'];

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

export function QuestionDisplay() {
  const { state } = useInterviewStore();
  const q = state.currentQuestion;
  if (!q) return null;
  return (
    <div className="bg-overlay/80 backdrop-blur rounded-xl p-4 shadow-lg">
      <div className="flex items-center gap-2 mb-2">
        <span className="px-2 py-0.5 bg-action-primary/10 text-action-primary text-[10px] font-semibold rounded">
          Q{q.question_number || '?'}
        </span>
        <span className="text-[10px] text-muted capitalize">{q.phase || state.session?.current_phase}</span>
      </div>
      <p className="text-sm text-primary leading-relaxed">{q.question}</p>
    </div>
  );
}

export function PhaseProgress() {
  const { state } = useInterviewStore();
  const currentPhase = state.session?.current_phase || 'intro';

  return (
    <div className="flex items-center justify-center gap-1 px-4 py-2">
      {PHASES.map((phase, i) => {
        const phaseIndex = PHASES.indexOf(currentPhase.toLowerCase());
        const isCompleted = phaseIndex > i;
        const isCurrent = phaseIndex === i;

        return (
          <React.Fragment key={phase}>
            {i > 0 && (
              <div className={`h-px flex-1 max-w-8 ${isCompleted || isCurrent ? 'bg-action-primary' : 'bg-border'}`} />
            )}
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-medium transition-colors ${
              isCurrent ? 'bg-action-primary/15 text-action-primary' : isCompleted ? 'text-success-text' : 'text-muted'
            }`}>
              <span className={`w-3.5 h-3.5 rounded-full flex items-center justify-center ${
                isCompleted ? 'bg-success-text text-inverse' : isCurrent ? 'bg-action-primary text-inverse' : 'bg-border text-muted'
              }`}>
                {isCompleted ? <Check className="w-2.5 h-2.5" /> : (i + 1)}
              </span>
              <span className="capitalize hidden sm:inline">{phase}</span>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
}

export function EvaluationFeedback({ entry }: { entry: { strengths: string[]; weaknesses: string[]; feedback: string; score: number } }) {
  const [open, setOpen] = React.useState(true);

  const scoreColor = (s: number) => s >= 7 ? 'text-success-text' : s >= 5 ? 'text-warning-text' : 'text-error-text';

  return (
    <div className="bg-elevated rounded-lg overflow-hidden text-xs">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-3 py-2 hover:bg-hover transition-colors">
        <span className="flex items-center gap-2">
          <span className={`font-bold text-sm ${scoreColor(entry.score)}`}>{entry.score.toFixed(1)}</span>
          <span className="text-muted">/ 10</span>
        </span>
        {open ? <ChevronUp className="w-3.5 h-3.5 text-muted" /> : <ChevronDown className="w-3.5 h-3.5 text-muted" />}
      </button>
      {open && (
        <div className="px-3 pb-2 space-y-1.5">
          {entry.feedback && <p className="text-secondary leading-relaxed">{entry.feedback}</p>}
          {entry.strengths.length > 0 && (
            <div>
              <span className="text-success-text font-medium">Strengths:</span>
              <ul className="list-disc list-inside text-muted mt-0.5 space-y-0.5">
                {entry.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {entry.weaknesses.length > 0 && (
            <div>
              <span className="text-warning-text font-medium">Improve:</span>
              <ul className="list-disc list-inside text-muted mt-0.5 space-y-0.5">
                {entry.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ConversationThread() {
  const { state } = useInterviewStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.evaluationHistory.length, state.currentQuestion]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4" data-conversation-thread>
      {state.evaluationHistory.map((entry, i) => (
        <div key={i} className="space-y-2 max-w-2xl mx-auto w-full">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-medium text-action-primary uppercase">Q{entry.questionNumber}</span>
            {entry.technicalScore != null && (
              <span className="text-[10px] text-muted">
                T:{entry.technicalScore.toFixed(1)} C:{entry.communicationScore?.toFixed(1)}
              </span>
            )}
          </div>
          <p className="text-sm text-primary bg-section/40 rounded-lg px-4 py-2.5">{entry.question}</p>
          <div className="ml-3 pl-3">
            <p className="text-sm text-secondary bg-elevated/60 rounded-lg px-4 py-2.5">{entry.answer}</p>
          </div>
          <EvaluationFeedback entry={{
            strengths: entry.strengths,
            weaknesses: entry.weaknesses,
            feedback: entry.feedback,
            score: entry.score,
          }} />
        </div>
      ))}

      {state.currentQuestion && (
        <div className="space-y-2 max-w-2xl mx-auto w-full">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-medium text-action-primary uppercase">Q{state.currentQuestion.question_number}</span>
            {state.currentQuestion.phase && (
              <span className="text-[10px] text-muted capitalize">Phase: {state.currentQuestion.phase}</span>
            )}
          </div>
          <p className="text-sm text-primary bg-section/60 rounded-xl px-5 py-3.5">{state.currentQuestion.question}</p>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
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

export function InputBar({ input, onInputChange, onSend, onKeyDown, isSending, placeholder = 'Type your answer...', children, statusIndicator }: InputBarProps) {
  const { state } = useInterviewStore();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 160) + 'px';
    }
  }, [input]);

  return (
    <div className="bg-page p-3 z-30">
      <div className="max-w-2xl mx-auto flex gap-3 items-end">
        {children}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={isSending ? 'Waiting for response...' : placeholder}
            rows={1}
            disabled={isSending}
            className="w-full px-4 py-2.5 pr-12 bg-input text-primary rounded-xl resize-none border-0 focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] disabled:opacity-50 transition-all text-sm placeholder-muted leading-relaxed"
          />
          <div className="absolute right-2 bottom-2 flex items-center gap-1">
            {input.length > 0 && (
              <span className="text-[10px] text-muted">{input.length}</span>
            )}
          </div>
        </div>
        <button
          onClick={onSend}
          disabled={!input.trim() || isSending || !state.currentQuestion}
          className="w-10 h-10 bg-action-primary text-inverse rounded-xl flex items-center justify-center hover:bg-action-primary-hover disabled:opacity-30 disabled:cursor-not-allowed transition-all shrink-0"
          title="Send (Enter)"
        >
          {isSending ? <Loader2 className="animate-spin w-4 h-4" /> : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          )}
        </button>
      </div>
      <div className="max-w-2xl mx-auto flex items-center justify-between mt-1">
        <span className="text-[10px] text-muted">Enter to send · Shift+Enter for newline</span>
        {statusIndicator && <span className="text-[10px] text-muted">{statusIndicator}</span>}
      </div>
    </div>
  );
}
