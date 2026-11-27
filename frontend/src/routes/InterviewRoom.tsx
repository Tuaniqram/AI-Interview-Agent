import { FileText, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useInterviewStore } from '../state/interviewStore';
import { ConductorRoom } from './interview/ConductorRoom';
import { PastEvaluationCard } from './interview/PastEvaluationCard';

export function InterviewRoom() {
  const navigate = useNavigate();
  const { state, actions } = useInterviewStore();
  const session = state.session;
  // Real interviews belong to an organization; practice sessions have none.
  const isPractice = !session?.org_id;

  const handleEnd = () => {
    actions.cancelInterview();
    navigate('/candidate/practice');
  };

  return (
    <div className="fixed inset-0 flex flex-col" data-theme="dark">
      <header className="shrink-0 h-12 flex items-center bg-page border-b border-border">
        <div className="flex-1 min-w-0 flex items-center gap-2.5 pl-4">
          <img src="/favicon.svg" className="w-6 h-6 shrink-0" alt="" />
          {session && (
            <>
              {isPractice ? (
                <span className="h-5 px-1.5 rounded-md bg-warning-bg text-warning-text text-xs font-medium flex items-center shrink-0">
                  Practice
                </span>
              ) : (
                <span className="h-5 px-1.5 rounded-md bg-action-primary-soft text-action-primary text-xs font-medium flex items-center shrink-0">
                  Interview
                </span>
              )}
              <span className="text-[13px] font-medium text-primary truncate">
                {session.job_role || 'AURA Interview'}
              </span>
              {!isPractice && (
                <span className="flex items-center gap-1.5 text-xs text-tertiary shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-error" aria-hidden /> Live
                </span>
              )}
            </>
          )}
        </div>

        <div className="flex justify-end items-center gap-2 pr-3">
          {isPractice && state.evaluationHistory.length > 0 && (
            <button
              onClick={actions.toggleCard}
              aria-pressed={state.cardVisible}
              className={`flex items-center gap-1.5 h-8 px-3 rounded-md border text-[13px] font-medium transition-colors ${
                state.cardVisible
                  ? 'border-transparent bg-action-primary-soft text-action-primary'
                  : 'border-border text-secondary hover:bg-hover hover:text-primary'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Realtime evaluation</span>
              {state.evaluationHistory.length > 0 && (
                <span className="bg-action-primary text-action-primary-text text-[11px] font-semibold px-1.5 rounded-md min-w-[18px] text-center tabular">
                  {state.evaluationHistory.length}
                </span>
              )}
            </button>
          )}

          {isPractice && (
            <button
              onClick={handleEnd}
              className="flex items-center gap-1.5 h-8 px-3 rounded-md border border-border text-[13px] font-medium text-secondary hover:bg-hover hover:text-primary transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>End anytime</span>
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 flex min-h-0 relative">
        <div className="flex-1 flex flex-col min-w-0">
          <ConductorRoom />
        </div>

        {state.cardVisible && (
          <div className="absolute right-4 top-4 z-50">
            <PastEvaluationCard />
          </div>
        )}
      </div>
    </div>
  );
}
