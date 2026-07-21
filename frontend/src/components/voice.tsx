import { Mic, Keyboard, Volume2, Wrench } from 'lucide-react';

export default function VoiceView() {
  return (
    <div className="min-h-[600px] bg-elevated rounded-xl p-8">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-action-primary rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Mic className="w-8 h-8 text-inverse" />
        </div>
        <h2 className="text-2xl font-bold text-primary mb-1">Voice Interview</h2>
        <p className="text-sm text-secondary">Speak your answers naturally and get real-time transcription</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="text-center p-4 bg-section rounded-xl">
          <Volume2 className="w-8 h-8 mx-auto mb-2 text-action-primary" />
          <div className="text-sm font-medium text-primary">Microphone</div>
        </div>
        <div className="text-center p-4 bg-section rounded-xl">
          <Mic className="w-8 h-8 mx-auto mb-2 text-info" />
          <div className="text-sm font-medium text-primary">Speech Recognition</div>
        </div>
        <div className="text-center p-4 bg-section rounded-xl">
          <Keyboard className="w-8 h-8 mx-auto mb-2 text-success" />
          <div className="text-sm font-medium text-primary">Speech Synthesis</div>
        </div>
      </div>

      <div className="bg-info-bg rounded-xl p-4 mb-8">
        <div className="flex items-start gap-2 text-info-text text-sm">
          <Wrench className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium mb-1">Voice Mode Coming Soon</p>
            <p className="opacity-80">
              This feature requires integration with speech-to-text (Web Speech API)
              for real-time transcription and text-to-speech (Web Speech API)
              for AI avatar responses.
            </p>
          </div>
        </div>
      </div>

      <div className="w-full max-w-md mx-auto">
        <div className="bg-section rounded-xl p-6">
          <div className="text-center space-y-4">
            <Mic className="w-12 h-12 mx-auto text-muted" />
            <div>
              <p className="text-primary font-medium text-sm">Voice Commands Ready</p>
              <p className="text-xs text-muted mt-1">
                Click to test microphone access
              </p>
            </div>
            <button className="px-5 py-2 bg-action-primary text-inverse text-sm font-medium rounded-lg hover:bg-action-primary-hover active:scale-[0.98] transition-all">
              Test Microphone
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
