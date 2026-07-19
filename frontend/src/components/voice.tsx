import React from 'react';
import { Mic, Keyboard, Volume2 } from 'lucide-react';

/**
 * Voice View Placeholder Component
 * Displays UI for voice-based interview mode
 * TODO: Integrate with speech recognition (Web Speech API) and speech synthesis
 */
export default function VoiceView() {
  return (
    <div className="min-h-[600px] bg-white rounded-2xl shadow-lg p-8">
      <div className="text-center mb-8">
        <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-10 h-10 text-white">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
        </div>
        <h2 className="text-3xl font-bold text-gray-800 mb-2">Voice Interview</h2>
        <p className="text-gray-600">Speak your answers naturally and get real-time transcription</p>
      </div>

      {/* Voice Utils Grid */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="text-center p-4 bg-blue-50 rounded-xl">
          <Volume2 className="w-10 h-10 mx-auto mb-2 text-blue-600" />
          <div className="text-sm font-medium text-gray-700">Microphone</div>
        </div>
        <div className="text-center p-4 bg-cyan-50 rounded-xl">
          <Mic className="w-10 h-10 mx-auto mb-2 text-cyan-600" />
          <div className="text-sm font-medium text-gray-700">Speech Recognition</div>
        </div>
        <div className="text-center p-4 bg-indigo-50 rounded-xl">
          <Keyboard className="w-10 h-10 mx-auto mb-2 text-indigo-600" />
          <div className="text-sm font-medium text-gray-700">Speech Synthesis</div>
        </div>
      </div>

      {/* Implementation Note */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-8">
        <div className="flex items-start gap-2 text-blue-800 text-sm">
          <span className="text-lg">🔧</span>
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

      {/* Demo Feature Preview */}
      <div className="w-full max-w-md mx-auto">
        <div className="bg-gray-50 rounded-xl p-6 border-2 border-dashed border-gray-300">
          <div className="text-center space-y-4">
            <Mic className="w-16 h-16 mx-auto text-gray-400" />
            <div>
              <p className="text-gray-700 font-medium">Voice Commands Ready</p>
              <p className="text-sm text-gray-500 mt-1">
                Click to test microphone access
              </p>
            </div>
            <button className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all">
              Test Microphone
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper icon component
