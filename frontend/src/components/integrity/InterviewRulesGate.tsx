import { ShieldAlert, Mic, Eye, ClipboardX } from 'lucide-react';

interface InterviewRulesGateProps {
  maxFlags: number | null;
  integrityEnabled: boolean;
  starting: boolean;
  onStart: () => void;
}

/**
 * Integrity rules screen shown before the interview session starts
 * (contract: docs/anti-cheat-guard.md §4.5). The candidate accepts the
 * conduct rules — including the flag limit when the guard is enabled — and
 * only then does the frontend start the interview.
 */
export function InterviewRulesGate({ maxFlags, integrityEnabled, starting, onStart }: InterviewRulesGateProps) {
  return (
    <div className="flex-1 h-full bg-page flex items-center justify-center overflow-y-auto" data-theme="dark">
      <div className="w-full max-w-md mx-4 my-8">
        <div className="rounded-2xl bg-overlay border border-border p-8 space-y-6 shadow-xl">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-action-primary/15 text-action-primary flex items-center justify-center shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-primary leading-tight">Interview conduct &amp; integrity</h2>
              <p className="text-secondary text-xs mt-1">
                Please read these rules before your interview begins.
              </p>
            </div>
          </div>

          <ul className="space-y-3 text-sm text-secondary">
            <li className="flex items-start gap-2.5">
              <Mic className="w-4 h-4 text-muted mt-0.5 shrink-0" />
              <span>
                Answer each question yourself. Do not read answers from another
                screen, document, or person.
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <Eye className="w-4 h-4 text-muted mt-0.5 shrink-0" />
              <span>
                Do not switch to other tabs, windows, or applications while a
                question is on screen. This is recorded as a focus-loss signal.
              </span>
            </li>
            <li className="flex items-start gap-2.5">
              <ClipboardX className="w-4 h-4 text-muted mt-0.5 shrink-0" />
              <span>
                Do not paste prepared answers. Answers should be your own,
                spoken or typed in the moment.
              </span>
            </li>
          </ul>

          {integrityEnabled && maxFlags != null && maxFlags > 0 && (
            <div className="rounded-xl bg-warning/10 border border-warning/25 px-4 py-3">
              <p className="text-xs text-warning font-medium">Integrity flags</p>
              <p className="text-secondary text-xs mt-1">
                This session is monitored. Each suspicious answer receives an
                integrity flag. If you reach{' '}
                <span className="text-primary font-semibold">{maxFlags} flags</span>,
                your interview session will be terminated and reviewed by the
                interviewer.
              </p>
            </div>
          )}

          <button
            onClick={onStart}
            disabled={starting}
            className="w-full py-3 rounded-xl bg-action-primary text-inverse text-sm font-medium hover:bg-action-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {starting ? 'Preparing your interview...' : 'I understand — start my interview'}
          </button>
        </div>
      </div>
    </div>
  );
}