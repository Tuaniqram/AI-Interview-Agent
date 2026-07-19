/**
 * App Root Component
 * Mode selector for different interview modes
 * Frontend architecture supports any future mode
 */

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useInterviewStore } from './state/interviewStore';
import { ProgressBar } from './components/shared/ProgressBar';
import { InterviewLayout } from './components/interview';
import StartView from './components/startView';
import { AvatarLayout } from './components/AvatarLayout';
import { AvatarPlaceholder } from './components/AvatarPlaceholder';
import { LipSyncTest } from './components/LipSyncTest';

type InterviewMode = 'typing' | 'voice' | 'avatar' | 'realtime' | 'lip-sync-test';

export function App() {
  const { state,actions } = useInterviewStore();
  const [selectedMode, setSelectedMode] = useState<InterviewMode>('typing');
  const [isLoading, setIsLoading] = useState(false);
  const [modeConfig, setModeConfig] = useState({
    companyId: 1001,
    jobRole: 'Software Engineer',
    apiURL: 'http://localhost:8000'
  });

  const handleModeSelect = (mode: InterviewMode) => {
    setSelectedMode(mode);
  };

  const renderModeContent = () => {
    switch (selectedMode) {
      case 'typing':
        return state.session ? (
          <InterviewLayout />
        ) : (
          <StartView
            onInterviewStart={async (params) => {
              setIsLoading(true);
              try {
                await actions.startInterview(params);
              } catch (error) {
                // Error handled by store
              } finally {
                setIsLoading(false);
              }
            }}
            modeConfig={modeConfig}
            onModeConfigChange={setModeConfig}
          />
        );

      case 'voice':
        // Voice mode - extension point, uses InterviewLayout for now
        return state.session ? (
          <InterviewLayout mode="voice" />
        ) : (
          <StartView
            onInterviewStart={async (params) => {
              setIsLoading(true);
              try {
                await actions.startInterview(params);
              } catch (error) {
                // Error handled by store
              } finally {
                setIsLoading(false);
              }
            }}
            modeConfig={modeConfig}
            onModeConfigChange={setModeConfig}
          />
        );

      case 'avatar':
        if (state.session) {
          return <AvatarLayout />;
        }
        return (
          <AvatarPlaceholder 
            onInterviewStart={async (params) => {
              setIsLoading(true);
              try {
                await actions.startInterview(params);
              } catch (error) {
                // Error handled by store
              } finally {
                setIsLoading(false);
              }
            }}
            modeConfig={modeConfig}
            onModeConfigChange={setModeConfig}
          />
        );

      case 'realtime':
        // Real-time conversation mode - future extension point
        return (
          <div className="text-center p-8">
            <h1 className="text-2xl font-bold text-gray-800 mb-4">
              Real-time AI Conversation
            </h1>
            <p className="text-gray-600">
              Coming soon - WebSocket-based real-time conversation mode
            </p>
          </div>
        );

      case 'lip-sync-test':
        return <LipSyncTest />;

      default:
        return <div>Invalid mode</div>;
    }
  };

  const isAvatarSession = selectedMode === 'avatar' && !!state.session;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-indigo-50 to-purple-100">
      {!isAvatarSession && (
        <>
          {/* Header */}
          <header className="text-center py-8">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-800 mb-2">
              🎯 AI Interview Agent
            </h1>
            <p className="text-gray-600">
              Intelligent Interview System with Multiple Modes
            </p>
          </header>

          {/* Mode Selector */}
          <div className="max-w-4xl mx-auto px-4 mb-8">
            <div className="flex justify-center gap-4 mb-8">
              {[
                { id: 'typing' as InterviewMode, label: 'Typing Mode', icon: '📝' },
                { id: 'voice' as InterviewMode, label: 'Voice Mode', icon: '🎤' },
                { id: 'avatar' as InterviewMode, label: 'Avatar Mode', icon: '🎭' },
                { id: 'realtime' as InterviewMode, label: 'Real-time', icon: '💬' },
                { id: 'lip-sync-test' as InterviewMode, label: 'Lip Sync Test', icon: '🔊' },
              ].map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => handleModeSelect(mode.id)}
                  className={`
                    px-6 py-3 rounded-lg font-semibold transition-all transform hover:scale-105
                    flex flex-col items-center gap-2
                    ${selectedMode === mode.id
                      ? 'bg-purple-600 text-white shadow-lg'
                      : 'bg-white text-gray-700 hover:bg-purple-50'
                    }
                  `}
                >
                  <span className="text-2xl">{mode.icon}</span>
                  <span>{mode.label}</span>
                </button>
              ))}
            </div>

            {/* Mode Description */}
            <div className="bg-white rounded-xl p-6 shadow-lg">
              <h2 className="font-semibold text-gray-800 mb-2">
                {selectedMode === 'typing' && 'Typing Mode: Traditional text-based interview'}
                {selectedMode === 'voice' && 'Voice Mode: Speech-to-text interview evaluation'}
                {selectedMode === 'avatar' && 'Avatar Mode: AI avatar interviewer for immersive experience'}
                {selectedMode === 'realtime' && 'Real-time Mode: Live conversation with instant feedback'}
              </h2>
            </div>
          </div>
        </>
      )}

      {/* Main Content */}
      <main className={isAvatarSession ? '' : 'max-w-4xl mx-auto px-4 pb-8'}>
        {isLoading && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-2xl p-8 text-center card-shadow">
              <Loader2 className="animate-spin w-12 h-12 text-purple-600 mx-auto mb-4" />
              <p className="text-gray-700 font-medium">Initializing {selectedMode} mode...</p>
            </div>
          </div>
        )}

        {state.currentQuestion && !isAvatarSession && (
          <div className="mb-6">
            <ProgressBar 
              current={state.currentQuestion.question_number}
              total={state.session?.total_questions || 1}
              label="Question"
            />
          </div>
        )}

        {renderModeContent()}

        {/* Error Display */}
        {state.error && (
          <div className="mt-6 bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
            <div className="flex items-center gap-2 text-red-700 font-medium">
              <span>❌</span>
              <span>Error: {state.error}</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}