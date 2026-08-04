import { FileText, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useInterviewStore } from '../state/interviewStore';
import { ConductorRoom } from './interview/ConductorRoom';
import { PastEvaluationCard } from './interview/PastEvaluationCard';

export function InterviewRoom() {
  const navigate = useNavigate();
  const { state, actions } = useInterviewStore();
  const session = state.session;
  const isPractice = !session?.department_id;

  const handleEnd = () => {
    actions.cancelInterview();
    navigate('/candidate/practice');
  };

  return (
    <div className="fixed inset-0 flex flex-col" data-theme="dark">
      <header className="shrink-0 flex items-center justify-center glass relative">
        <div className="flex-1 flex items-center gap-2 pl-3">
          {session && (
            <>
              {isPractice ? (
                <span className="px-2 py-1 rounded-md bg-amber-500/15 text-amber-400 text-[10px] font-semibold uppercase tracking-wider">
                  Practice
                </span>
              ) : (
                <span className="px-2 py-1 rounded-md bg-action-primary/15 text-action-primary text-[10px] font-semibold uppercase tracking-wider">
                  Interview
                </span>
              )}
              <span className="text-xs text-secondary truncate max-w-[40vw]">
                {session.job_role || 'AURA Interview'}
                {!isPractice && session.department_id ? ' · Live' : ''}
              </span>
            </>
          )}
        </div>

        <div className="flex-1 flex justify-end items-center gap-2 pr-3">
          {isPractice && state.evaluationHistory.length > 0 && (
            <button
              onClick={actions.toggleCard}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                state.cardVisible
                  ? 'bg-action-primary/20 text-action-primary'
                  : 'bg-overlay text-secondary hover:bg-hover'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Realtime Evaluation</span>
              {state.evaluationHistory.length > 0 && (
                <span className="bg-action-primary text-inverse text-[9px] font-bold px-1 rounded-full min-w-[14px] text-center">
                  {state.evaluationHistory.length}
                </span>
              )}
            </button>
          )}

          {isPractice && (
            <button
              onClick={handleEnd}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-overlay text-secondary hover:bg-hover transition-colors"
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
