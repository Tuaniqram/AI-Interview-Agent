import { FileText } from 'lucide-react';
import { useInterviewStore } from '../state/interviewStore';
import { TypingMode } from './interview/TypingMode';
import { VoiceMode } from './interview/VoiceMode';
import { AvatarMode } from './interview/AvatarMode';
import { PastEvaluationCard } from './interview/PastEvaluationCard';
import { PhaseProgress } from './interview/shared';

export function InterviewRoom() {
  const { state, actions } = useInterviewStore();
  const mode = state.interviewMode || 'avatar';

  const modeEl = (() => {
    switch (mode) {
      case 'typing':
        return <TypingMode />;
      case 'voice':
        return <VoiceMode />;
      case 'avatar':
      default:
        return <AvatarMode />;
    }
  })();

  return (
    <div className="fixed inset-0 flex flex-col" data-theme="dark">
      <header className="shrink-0 flex items-center justify-center bg-page/80 backdrop-blur-sm relative">
        <div className="flex-1" />
        <PhaseProgress />
        <div className="flex-1 flex justify-end pr-3">
          <button
            onClick={actions.toggleCard}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              state.evaluationHistory.length > 0
                ? 'bg-action-primary/10 text-action-primary hover:bg-action-primary/20'
                : 'bg-overlay text-secondary hover:bg-hover'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Evaluations</span>
            {state.evaluationHistory.length > 0 && (
              <span className="bg-action-primary text-inverse text-[9px] font-bold px-1 rounded-full min-w-[14px] text-center">
                {state.evaluationHistory.length}
              </span>
            )}
          </button>
        </div>
      </header>

      <div className="flex-1 flex min-h-0 relative">
        <div className="flex-1 flex flex-col min-w-0">
          {modeEl}
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
