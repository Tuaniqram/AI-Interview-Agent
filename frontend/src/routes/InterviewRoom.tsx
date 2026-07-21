import { useInterviewStore } from '../state/interviewStore';
import { TypingMode } from './interview/TypingMode';
import { VoiceMode } from './interview/VoiceMode';
import { AvatarMode } from './interview/AvatarMode';

export function InterviewRoom() {
  const { state } = useInterviewStore();
  const mode = state.interviewMode || 'avatar';

  switch (mode) {
    case 'typing':
      return <TypingMode />;
    case 'voice':
      return <VoiceMode />;
    case 'avatar':
    default:
      return <AvatarMode />;
  }
}
