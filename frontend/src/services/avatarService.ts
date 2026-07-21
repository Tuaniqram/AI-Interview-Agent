/**
 * Avatar Service - Extension points for avatar interviewer mode
 * FUTURE: Will connect to avatar generation and control APIs
 * CURRENT: Provides interface for future avatar functionality
 */

import { 
  AvatarState, 
  AvatarEmotion, 
  SpeakingSpeed 
} from '../types/avatar';

/**
 * Avatar Service - Tier 2: API Layer
 * 
 * Extension Points Design:
 * TODO: When backend implements avatar APIs, add methods here:
 * 
 * 1. POST /avatars/load - Load avatar configuration
 * 2. POST /avatars/state/update - Update avatar emotion/state
 * 3. POST /avatars/sync - Sync avatar audio/video with backend
 * 4. GET /avatars/voice - Get avatar voice profile
 * 5. POST /avatars/preview - Preview avatar behavior
 */

export class AvatarService {
  // ========== PLACEHOLDER METHODS ==========
  
  /**
   * Load avatar configuration (Future API)
   * POST /avatars/{company_id}/config
   */
  async loadAvatar(_configId: string): Promise<AvatarState> {
    // TODO: Implement when backend provides avatar configuration API
    console.log('AvatarService: loadAvatar() - Placeholder');
    return {
      emotion: 'neutral',
      speakingSpeed: 'normal',
      isSpeaking: false,
      isListening: false,
      isThinking: false,
    };
  }

  /**
   * Update avatar emotion and state (Future API)
   * POST /avatars/{session_id}/state/update
   */
  async updateAvatarState(params: {
    session_id: string;
    emotion: AvatarEmotion;
    speed: SpeakingSpeed;
    isSpeaking: boolean;
    isListening: boolean;
    isThinking: boolean;
  }): Promise<AvatarState> {
    // TODO: Implement when backend provides avatar state control API
    console.log('AvatarService: updateAvatarState() - Placeholder');
    return {
      emotion: params.emotion,
      speakingSpeed: params.speed,
      isSpeaking: params.isSpeaking,
      isListening: params.isListening,
      isThinking: params.isThinking,
    };
  }

  /**
   * Get avatar speaking speed (Future API)
   * GET /avatars/{session_id}/voice/speed
   */
  async getAvatarVoiceSpeed(_session_id: string): Promise<SpeakingSpeed> {
    // TODO: Implement when backend provides voice control API
    console.log('AvatarService: getAvatarVoiceSpeed() - Placeholder');
    return 'normal';
  }

  /**
   * Sync avatar to backend (Future API - for WebSocket/WebRTC)
   * POST /avatars/{session_id}/sync
   */
  async syncAvatar(_session_id: string): Promise<{ synced: boolean }> {
    // TODO: Implement when backend provides avatar sync API
    console.log('AvatarService: syncAvatar() - Placeholder');
    return { synced: true };
  }
}

// Export singleton instance
export const avatarService = new AvatarService();