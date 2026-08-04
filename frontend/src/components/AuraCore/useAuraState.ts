import { useInterviewStore } from '../../state/interviewStore';
import type { AuraState } from './types';

/**
 * Maps live interview state (WS engine phases + store flags) to AuraCore states.
 *   evaluating       → thinking   (engine analysing the answer)
 *   question_ready   → responding (conductor delivering the next question)
 *   reconnecting     → thinking   (link to the engine being re-established)
 *   question awaiting → listening (conductor waiting on the candidate)
 *   completed/no session → idle
 */
export function useAuraState(): AuraState {
  const { state } = useInterviewStore();

  if (!state.session) return 'idle';
  if (state.session.status === 'completed') return 'idle';
  if (state.wsPhase === 'evaluating' || state.isEvaluating) return 'thinking';
  if (state.isLoading) return 'thinking';
  if (state.wsPhase === 'reconnecting') return 'thinking';
  if (state.wsPhase === 'question_ready') return 'responding';
  if (state.currentQuestion) return 'listening';
  return 'idle';
}
