import React from 'react';
import { Volume2, Wifi, WifiOff, TestTube } from 'lucide-react';
import { AvatarRenderer, getLipSyncController } from './AvatarRenderer';
import type { VisemeEvent } from '../avatar/types';

const CHAR_TO_PHONEME: Record<string, string> = {
  a: 'AA', b: 'B', c: 'K', d: 'D',
  e: 'EH', f: 'F', g: 'G', h: 'HH',
  i: 'IH', j: 'JH', k: 'K', l: 'L',
  m: 'M', n: 'N', o: 'OW', p: 'P',
  q: 'K', r: 'R', s: 'S', t: 'T',
  u: 'UH', v: 'V', w: 'W', x: 'K',
  y: 'Y', z: 'Z',
}

function textToVisemes(text: string): VisemeEvent[] {
  const lower = text.toLowerCase()
  const chars = lower.split('')
  const visemes: VisemeEvent[] = []
  let time = 0
  const charDuration = 0.08

  for (const ch of chars) {
    if (!ch.match(/[a-z]/)) {
      time += charDuration
      continue
    }
    const phoneme = CHAR_TO_PHONEME[ch] ?? 'SIL'
    visemes.push({ time, value: phoneme, intensity: 0.8, duration: charDuration })
    time += charDuration
  }

  visemes.push({ time, value: 'SIL', intensity: 0, duration: 0.1 })
  return visemes
}

export function LipSyncTest() {
  const [text, setText] = React.useState('Hello, I am your AI interviewer. How are you today?');
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  const [connected, setConnected] = React.useState(false);

  React.useEffect(() => {
    const id = setInterval(() => {
      const lc = getLipSyncController();
      if (lc) {
        clearInterval(id);
        lc.onConnected = () => setConnected(true);
        lc.connect('test-session', 'localhost:8000');
      }
    }, 100);
    return () => {
      clearInterval(id);
      const lc = getLipSyncController();
      if (lc) {
        lc.onConnected = null;
        lc.disconnect();
      }
      setConnected(false);
    };
  }, []);

  React.useEffect(() => {
    const id = setInterval(() => {
      setIsSpeaking(getLipSyncController()?.isSpeaking ?? false);
    }, 100);
    return () => clearInterval(id);
  }, []);

  const handleSpeak = () => {
    if (!text.trim()) return;
    getLipSyncController()?.speak(text.trim());
  };

  const handleLocalTest = () => {
    const lc = getLipSyncController()
    if (!lc) return
    const visemes = textToVisemes(text.trim())
    const totalDuration = visemes[visemes.length - 1]?.time ?? 1
    lc.testLocal(visemes, totalDuration + 0.3)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSpeak();
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-900 flex flex-col">
      <div className="relative flex-1 min-h-0">
        <AvatarRenderer
          emotion={isSpeaking ? 'excited' : 'neutral'}
          activeViseme={null}
          isSpeaking={isSpeaking}
          isListening={false}
          className="w-full h-full"
        />
      </div>

      <div className="bg-gray-900 -t -gray-800 p-3 z-30">
        <div className="max-w-2xl mx-auto flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type text for the avatar to speak..."
              rows={2}
              className="w-full px-4 py-2.5 bg-gray-800 text-white  -gray-700 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:-transparent transition-all text-sm placeholder-gray-500"
            />
          </div>
          <button
            onClick={handleSpeak}
            disabled={!text.trim() || !connected}
            className="h-11 px-6 bg-purple-600 text-white rounded-xl flex items-center gap-2 hover:bg-purple-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all shrink-0"
          >
            <Volume2 className="w-5 h-5" />
            Speak
          </button>
          <button
            onClick={handleLocalTest}
            disabled={!text.trim()}
            className="h-11 px-4 bg-green-700 text-white rounded-xl flex items-center gap-2 hover:bg-green-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all shrink-0"
          >
            <TestTube className="w-5 h-5" />
            Local Test
          </button>
        </div>

        <div className="max-w-2xl mx-auto flex items-center gap-3 mt-2 text-[11px] text-gray-500">
          {connected ? (
            <span className="flex items-center gap-1 text-green-500">
              <Wifi className="w-3 h-3" />
              WebSocket connected
            </span>
          ) : (
            <span className="flex items-center gap-1 text-yellow-500">
              <WifiOff className="w-3 h-3" />
              Connecting...
            </span>
          )}
          {isSpeaking && (
            <span className="flex items-center gap-1 text-purple-400">
              <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse" />
              Speaking...
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
