import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, ArrowLeft, Check, ChevronDown, ChevronUp } from 'lucide-react';
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
        className="flex items-center gap-1.5 px-3 py-1.5 bg-overlay text-secondary rounded-lg text-xs hover:bg-hover transition-colors">
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
      <div className="text-center space-y-4 max-w-xs px-4">
        <Loader2 className="animate-spin w-12 h-12 text-action-primary mx-auto" />
        <p className="text-secondary">{label}</p>
        {slow && (
          <p className="text-muted text-xs">
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
    <div className="glass rounded-xl p-4 shadow-lg">
      <div className="flex items-center gap-2 mb-2">
        <span className="px-2 py-0.5 bg-action-primary/10 text-action-primary text-[10px] font-semibold rounded">
          Q{q.question_number || '?'}
        </span>
        <span className="text-[10px] text-muted capitalize">{humanizePhase(q.phase || state.session?.current_phase)}</span>
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

function scoreTone(s: number | null) {
  if (s === null) return 'text-muted';
  return s >= 7 ? 'text-success-text' : s >= 5 ? 'text-warning-text' : 'text-error-text';
}

type HistoryEntry = ReturnType<typeof useInterviewStore>['state']['evaluationHistory'][number];

/** Full feedback for one answer: score, summary, then strengths / improvements side by side. */
function FeedbackPanel({ entry }: { entry: HistoryEntry }) {
  return (
    <div className="rounded-xl bg-elevated/70 p-4 space-y-3">
      <div className="flex items-baseline gap-1.5">
        {entry.score === null ? (
          <span className="text-base font-semibold text-muted">Not scored</span>
        ) : (
          <>
            <span className={`text-3xl font-bold leading-none ${scoreTone(entry.score)}`}>{entry.score.toFixed(1)}</span>
            <span className="text-sm text-muted">/ 10</span>
          </>
        )}
        <span className="ml-2 text-sm text-muted">Feedback on your answer</span>
      </div>
      {entry.feedback && <p className="text-base text-secondary leading-relaxed">{entry.feedback}</p>}
      {(entry.strengths.length > 0 || entry.weaknesses.length > 0) && (
        <div className="grid gap-3 sm:grid-cols-2">
          {entry.strengths.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-success-text mb-1">Did well</p>
              <ul className="space-y-1 text-sm text-secondary leading-relaxed list-disc list-inside">
                {entry.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {entry.weaknesses.length > 0 && (
            <div>
              <p className="text-sm font-semibold text-warning-text mb-1">To improve</p>
              <ul className="space-y-1 text-sm text-secondary leading-relaxed list-disc list-inside">
                {entry.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** One earlier question: a single readable row that opens to the question, the answer and the feedback. */
function EarlierAnswer({ entry, showEvaluation }: { entry: HistoryEntry; showEvaluation: boolean }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="rounded-xl border border-[var(--border-color)]/60 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-hover/50 transition-colors"
      >
        <span className="text-sm font-semibold text-action-primary shrink-0">Q{entry.questionNumber}</span>
        <span className="flex-1 min-w-0 text-sm text-secondary truncate">{entry.question || entry.conversationTurn}</span>
        {showEvaluation && (
          <span className={`text-sm font-semibold shrink-0 ${scoreTone(entry.score)}`}>
            {entry.score === null ? '—' : entry.score.toFixed(1)}
          </span>
        )}
        {open ? <ChevronUp className="w-4 h-4 text-muted shrink-0" /> : <ChevronDown className="w-4 h-4 text-muted shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3">
          <p className="text-base text-primary leading-relaxed">{entry.conversationTurn || entry.question}</p>
          <div className="pl-3 border-l-2 border-action-primary/40">
            <p className="text-xs uppercase tracking-wide text-muted mb-1">Your answer</p>
            <p className="text-base text-secondary leading-relaxed whitespace-pre-wrap">{entry.answer}</p>
          </div>
          {showEvaluation && <FeedbackPanel entry={entry} />}
        </div>
      )}
    </div>
  );
}

/**
 * The current question comes first so it is always on screen; feedback on the latest answer sits right under it,
 * and everything earlier is a collapsed row (newest first). No scrolling to find where you are.
 */
export function ConversationThread({ showEvaluation = true }: { showEvaluation?: boolean }) {
  const { state } = useInterviewStore();
  const topRef = useRef<HTMLDivElement>(null);
  const history = state.evaluationHistory;
  const latest = history[history.length - 1];
  const earlier = history.slice(0, -1).reverse();
  const q = state.currentQuestion;
  const total = state.session?.total_questions ?? 0;

  useEffect(() => {
    topRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [q?.question_number]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4" data-conversation-thread>
      <div ref={topRef} className="max-w-3xl mx-auto w-full space-y-4">
        {q && (
          <section aria-label="Current question" className="rounded-2xl bg-section/70 px-6 py-5 space-y-3">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
              <span className="font-semibold text-action-primary">
                Question {q.question_number}{total >= q.question_number ? ` of ${total}` : ''}
              </span>
              {q.phase && <span className="text-muted">{humanizePhase(q.phase)}</span>}
            </div>
            <p className="text-xl text-primary leading-relaxed">{state.conversationTurn || q.question}</p>
          </section>
        )}

        {showEvaluation && latest && (
          <section aria-label={`Feedback on question ${latest.questionNumber}`} className="space-y-2">
            <p className="text-sm text-muted">Your answer to Q{latest.questionNumber}</p>
            <p className="text-base text-secondary leading-relaxed whitespace-pre-wrap pl-3 border-l-2 border-action-primary/40">
              {latest.answer}
            </p>
            <FeedbackPanel entry={latest} />
          </section>
        )}

        {!showEvaluation && latest && (
          <EarlierAnswer entry={latest} showEvaluation={false} />
        )}

        {earlier.length > 0 && (
          <section aria-label="Earlier questions" className="space-y-2">
            <p className="text-sm text-muted pt-2">Earlier questions</p>
            {earlier.map((entry) => (
              <EarlierAnswer key={entry.questionNumber} entry={entry} showEvaluation={showEvaluation} />
            ))}
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

  return (
    <div className="bg-page p-3 z-30">
      <div className="max-w-3xl mx-auto flex gap-3 items-end">
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
            aria-label="Type your answer"
            className="w-full px-4 py-2.5 pr-12 bg-input text-primary rounded-xl resize-none border-0 focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] disabled:opacity-50 transition-all text-base placeholder-muted leading-relaxed"
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
      <div className="max-w-3xl mx-auto flex items-center justify-between mt-1">
        <span className="text-xs text-muted">Enter to send · Shift+Enter for newline</span>
        {statusIndicator && <span className="text-[10px] text-muted">{statusIndicator}</span>}
      </div>
    </div>
  );
}
