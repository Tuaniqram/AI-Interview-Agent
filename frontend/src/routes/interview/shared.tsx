import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, ArrowLeft, ArrowUp, Check, ChevronDown, ChevronUp } from 'lucide-react';
import { useInterviewStore } from '../../state/interviewStore';

const PHASES = ['intro', 'experience', 'technical', 'behavioral', 'conclusion'];

const PHASE_LABELS: Record<string, string> = {
  tech_db: 'Databases', tech_devops: 'DevOps', tech_core: 'Core technical', tech_system_design: 'System design',
  tech_framework: 'Frameworks', tech_stack: 'Tech stack', tech_testing: 'Testing', tech_data: 'Data',
  tech_security: 'Security', tech_caching: 'Caching', tech_mobile: 'Mobile', tech_event_driven: 'Event-driven systems',
};

/** Internal phase/competency ids (e.g. "cog_problem_solving") -> text a candidate can read. */
export function humanizePhase(raw?: string | null): string {
  if (!raw) return '';
  const key = raw.toLowerCase();
  if (PHASE_LABELS[key]) return PHASE_LABELS[key];
  const text = key.replace(/^(cog|behav|beh|tech|soft)_/, '').replace(/_/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}


export function BackButton() {
  const navigate = useNavigate();
  return (
    <div className="absolute top-3 start-3 z-30">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1.5 h-8 px-3 rounded-md border border-border bg-section text-secondary text-[13px] hover:text-primary hover:border-border-strong transition-colors">
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>
    </div>
  );
}

export function LoadingScreen({ label = 'Preparing interview...' }: { label?: string }) {
  // Preparing an interview (role profile, company context, strategy, first question) can take a
  // minute or more: say so, instead of an unexplained spinner that looks stuck.
  const [slow, setSlow] = React.useState(false);
  React.useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 15000);
    return () => clearTimeout(timer);
  }, []);
  return (
    <div className="fixed inset-0 bg-page flex items-center justify-center" data-theme="dark" role="status" aria-live="polite">
      <div className="text-center max-w-xs px-4">
        <Loader2 className="animate-spin w-6 h-6 text-action-primary mx-auto" />
        <p className="mt-4 text-sm text-primary">{label}</p>
        {slow && (
          <p className="mt-2 text-[13px] text-tertiary leading-relaxed">
            Tailoring the interview to the role takes a little while the first time. Please keep this tab open.
          </p>
        )}
      </div>
    </div>
  );
}

export function QuestionDisplay() {
  const { state } = useInterviewStore();
  const q = state.currentQuestion;
  if (!q) return null;
  return (
    <div className="rounded-xl border border-border bg-section p-4">
      <div className="flex items-center gap-2 mb-2 text-xs">
        <span className="font-semibold text-action-primary">Question {q.question_number || '?'}</span>
        <span className="text-tertiary">{humanizePhase(q.phase || state.session?.current_phase)}</span>
      </div>
      <p className="text-[15px] text-primary leading-relaxed">{q.question}</p>
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

export function EvaluationFeedback({ entry }: { entry: { strengths: string[]; weaknesses: string[]; feedback: string; score: number | null } }) {
  const [open, setOpen] = React.useState(true);

  const scoreColor = (s: number) => s >= 7 ? 'text-success-text' : s >= 5 ? 'text-warning-text' : 'text-error-text';

  return (
    <div className="bg-elevated rounded-lg overflow-hidden text-xs">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-3 py-2 hover:bg-hover transition-colors">
        <span className="flex items-center gap-2">
          {entry.score === null ? (
            <span className="font-semibold text-sm text-muted">Not scored</span>
          ) : (
            <>
              <span className={`font-bold text-sm ${scoreColor(entry.score)}`}>{entry.score.toFixed(1)}</span>
              <span className="text-muted">/ 10</span>
            </>
          )}
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

type HistoryEntry = ReturnType<typeof useInterviewStore>['state']['evaluationHistory'][number];

/** One earlier question: a single readable row that opens to the question and your answer. Scores live in the corner card. */
function EarlierAnswer({ entry }: { entry: HistoryEntry }) {
  const [open, setOpen] = React.useState(false);
  return (
    <li>
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="w-full flex items-center gap-3 px-4 h-12 text-left hover:bg-hover/60 transition-colors"
      >
        <span className="w-6 h-6 rounded-md bg-hover text-secondary text-xs font-semibold flex items-center justify-center shrink-0 tabular">
          {entry.questionNumber}
        </span>
        <span className="flex-1 min-w-0 text-sm text-secondary truncate">{entry.question || entry.conversationTurn}</span>
        {open ? <ChevronUp className="w-4 h-4 text-tertiary shrink-0" /> : <ChevronDown className="w-4 h-4 text-tertiary shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4 pl-[3.25rem] space-y-3">
          <p className="text-[15px] text-primary leading-relaxed">{entry.conversationTurn || entry.question}</p>
          <div className="rounded-lg bg-page border border-border px-4 py-3">
            <p className="text-xs text-tertiary mb-1">Your answer</p>
            <p className="text-[15px] text-secondary leading-relaxed whitespace-pre-wrap">{entry.answer}</p>
          </div>
        </div>
      )}
    </li>
  );
}

/**
 * The current question is first so it is always on screen; earlier questions are collapsed rows (newest first).
 * Evaluations never appear here: they open from the "Realtime Evaluation" button in the corner card.
 */
export function ConversationThread() {
  const { state } = useInterviewStore();
  const topRef = useRef<HTMLDivElement>(null);
  const earlier = [...state.evaluationHistory].reverse();
  const q = state.currentQuestion;
  const total = state.session?.total_questions ?? 0;

  useEffect(() => {
    topRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [q?.question_number]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 sm:py-10" data-conversation-thread>
      <div ref={topRef} className="max-w-3xl mx-auto w-full space-y-8">
        {q && (
          <section aria-label="Current question" aria-live="polite">
            <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px]">
              <span className="font-medium text-action-primary">
                Question {q.question_number}{total >= q.question_number ? ` of ${total}` : ''}
              </span>
              {q.phase && (<><span className="text-border-strong" aria-hidden>/</span><span className="text-tertiary">{humanizePhase(q.phase)}</span></>)}
            </p>
            <p className="mt-3 text-[22px] sm:text-2xl leading-[1.45] tracking-[-0.01em] text-primary max-w-[60ch]">
              {state.conversationTurn || q.question}
            </p>
          </section>
        )}

        {earlier.length > 0 && (
          <section aria-label="Earlier questions">
            <h2 className="text-[13px] text-tertiary mb-2">Earlier questions</h2>
            <ul className="rounded-xl border border-border bg-section divide-y divide-[var(--divider)] overflow-hidden">
              {earlier.map((entry) => (
                <EarlierAnswer key={entry.questionNumber} entry={entry} />
              ))}
            </ul>
          </section>
        )}
      </div>
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

  // A composer: the answer box with its tools underneath, like a message field, not a lone input.
  return (
    <div className="shrink-0 bg-page px-3 sm:px-4 pb-3 sm:pb-4 pt-2 z-30">
      <div className="max-w-3xl mx-auto rounded-xl border border-border-strong bg-section shadow-sm focus-within:border-[var(--action-primary)] focus-within:ring-[3px] focus-within:ring-[var(--focus-ring)] transition-colors">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={isSending ? 'Waiting for response...' : placeholder}
          rows={1}
          disabled={isSending}
          aria-label="Type your answer"
          className="block w-full px-4 pt-3 pb-1 bg-transparent text-primary resize-none border-0 focus:outline-none disabled:opacity-50 text-[15px] placeholder:text-tertiary leading-relaxed"
        />
        <div className="flex items-center gap-2 px-2 pb-2">
          {children}
          {statusIndicator && <span className="flex items-center gap-3 text-xs text-tertiary min-w-0">{statusIndicator}</span>}
          <span className="ml-auto flex items-center gap-3">
            {input.length > 0 && <span className="text-xs text-tertiary tabular">{input.length}</span>}
            <button
              onClick={onSend}
              disabled={!input.trim() || isSending || !state.currentQuestion}
              className="w-8 h-8 bg-action-primary text-action-primary-text rounded-lg flex items-center justify-center hover:bg-action-primary-hover disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
              title="Send (Enter)"
              aria-label="Send answer"
            >
              {isSending ? <Loader2 className="animate-spin w-4 h-4" /> : <ArrowUp className="w-4 h-4" />}
            </button>
          </span>
        </div>
      </div>
      <p className="max-w-3xl mx-auto mt-1.5 px-1 text-xs text-tertiary">Enter to send, Shift+Enter for a new line</p>
    </div>
  );
}
