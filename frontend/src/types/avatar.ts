/**
 * Avatar-related types for future avatar interviewer implementation
 * Future API contract example when backend returns avatar data
 */

import { Question } from './interview';

export type AvatarEmotion = 'neutral' | 'happy' | 'thoughtful' | 'concerned' | 'confident' | 'surprised' | 'laughing' | 'considering' | 'excited';

export type SpeakingSpeed = 'slow' | 'normal' | 'fast';

export interface AvatarState {
  emotion: AvatarEmotion;
  speakingSpeed: SpeakingSpeed;
  isSpeaking: boolean;
  isListening: boolean;
  isThinking: boolean;
  avatarId?: string;
}

/**
 * Avatar question with backend metadata for avatar rendering
 */
export interface AvatarQuestion extends Question {
  avatarData?: {
    emotion: AvatarEmotion;
    speakingSpeed: SpeakingSpeed;
    visualEmoji?: string;
    facialExpression?: string;
  };
}