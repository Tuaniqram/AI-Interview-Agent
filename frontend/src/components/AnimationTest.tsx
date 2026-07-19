import React from 'react';
import { AvatarRenderer, getLipSyncController } from './AvatarRenderer';
import type { AvatarEmotion } from '../types/avatar';

const BODY_STATES = ['idle', 'speaking', 'listening', 'thinking'] as const;
type BodyState = typeof BODY_STATES[number];

const EMOTIONS: { key: AvatarEmotion; label: string; icon: string }[] = [
  { key: 'neutral', label: 'Neutral', icon: 'N' },
  { key: 'laughing', label: 'Laughing', icon: 'L' },
  { key: 'considering', label: 'Considering', icon: 'C' },
  { key: 'excited', label: 'Excited', icon: 'E' },
  { key: 'thoughtful', label: 'Thoughtful', icon: 'T' },
];

const GESTURES = [
  'openPalm', 'singleHandEmphasis', 'bothHandsOpen', 'forearmLift',
  'palmUpward', 'smallPointing', 'shoulderEmphasis', 'chestEmphasis',
  'fingerEmphasis', 'handRotation', 'smallShrug', 'questionEmphasis',
  'agreementNod', 'explanationGesture', 'closingGesture',
] as const;

function btnCls(active: boolean): string {
  return `px-3 py-1.5 text-xs rounded-lg font-medium transition-all border ${active ? 'bg-purple-600 text-white border-purple-600' : 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700'}`;
}

export function AnimationTest() {
  const [bodyState, setBodyState] = React.useState<BodyState>('idle');
  const [emotion, setEmotion] = React.useState<AvatarEmotion>('neutral');
  const [isListening, setIsListening] = React.useState(false);
  const [connected, setConnected] = React.useState(false);
  const [speaking, setSpeaking] = React.useState(false);
  const [text, setText] = React.useState('Hello, I am your AI interviewer.');
  const [debugMode, setDebugMode] = React.useState(false);
  const [debugInfo, setDebugInfo] = React.useState<string>('No gesture active');
  const [activeGesture, setActiveGesture] = React.useState<string | null>(null);

  React.useEffect(() => {
    const id = setInterval(() => {
      const lc = getLipSyncController();
      if (lc) {
        clearInterval(id);
        lc.connect('anim-test-session', 'localhost:8000');
        lc.onConnected = () => setConnected(true);
      }
    }, 100);
    return () => {
      clearInterval(id);
      getLipSyncController()?.disconnect();
      setConnected(false);
    };
  }, []);

  React.useEffect(() => {
    const id = setInterval(() => {
      setSpeaking(getLipSyncController()?.isSpeaking ?? false);
    }, 100);
    return () => clearInterval(id);
  }, []);

  React.useEffect(() => {
    (window as any).DEBUG_GESTURES = debugMode;
  }, [debugMode]);

  React.useEffect(() => {
    const id = setInterval(() => {
      const debug = (window as any).__lastGestureDebug;
      if (debug) {
        const rotStr = debug.bones.map((b: string) => {
          const r = debug.targets[b]?.rotation;
          return r ? `${b}: [${r.map((v: number) => v.toFixed(3)).join(', ')}]` : b;
        }).join(' | ');
        setDebugInfo(
          `Gesture: ${debug.gesture}\n` +
          `State: ${debug.state}\n` +
          `Progress: ${debug.progress.toFixed(2)}\n` +
          `Phase: ${debug.phaseIndex}\n` +
          `Elapsed: ${debug.elapsed.toFixed(2)}s\n` +
          `Bones: ${rotStr}`
        );
        setActiveGesture(debug.gesture);
      } else {
        setDebugInfo('No gesture active');
        setActiveGesture(null);
      }
    }, 100);
    return () => clearInterval(id);
  }, []);

  const triggerGesture = (g: string) => {
    const lc = getLipSyncController();
    if (lc) {
      if (lc.hasActiveGesture()) {
        lc.stopGesture();
      }
      lc.triggerGesture(g as any);
    }
  };

  const stopCurrentGesture = () => {
    getLipSyncController()?.stopGesture();
  };

  const effectiveSpeaking = speaking || bodyState === 'speaking';

  const gestureLabels: Record<string, string> = {
    openPalm: 'Open Palm',
    singleHandEmphasis: 'Single Hand',
    bothHandsOpen: 'Both Hands',
    forearmLift: 'Forearm Lift',
    palmUpward: 'Palm Up',
    smallPointing: 'Point',
    shoulderEmphasis: 'Shoulder',
    chestEmphasis: 'Chest',
    fingerEmphasis: 'Finger',
    handRotation: 'Hand Rotate',
    smallShrug: 'Shrug',
    questionEmphasis: 'Question',
    agreementNod: 'Nod',
    explanationGesture: 'Explain',
    closingGesture: 'Closing',
  };

  return (
    <div className="fixed inset-0 bg-gray-900 flex">
      <div className="flex-1 relative">
        <AvatarRenderer
          emotion={emotion}
          activeViseme={null}
          isSpeaking={effectiveSpeaking}
          isListening={isListening}
          className="w-full h-full"
        />
        {debugMode && (
          <div className="absolute top-2 right-2 bg-black/70 text-green-400 text-[10px] font-mono p-2 rounded whitespace-pre leading-tight max-w-xs">
            {debugInfo}
          </div>
        )}
      </div>

      <div className="w-80 bg-gray-800/80 border-l border-gray-700 overflow-y-auto p-4 space-y-5">
        <h2 className="text-white font-bold text-sm tracking-wide">Animation Test</h2>

        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-gray-400 text-xs font-semibold uppercase">Debug</h3>
            <label className="flex items-center gap-1.5 text-gray-400 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={debugMode}
                onChange={(e) => setDebugMode(e.target.checked)}
                className="rounded"
              />
              Gesture Debug
            </label>
          </div>
          <div className="flex gap-1.5">
            <button
              onClick={stopCurrentGesture}
              disabled={!activeGesture}
              className="flex-1 px-2 py-1.5 text-xs rounded-lg font-medium bg-red-800 text-red-200 border border-red-700 hover:bg-red-700 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Stop Gesture
            </button>
          </div>
        </section>

        <section>
          <h3 className="text-gray-400 text-xs font-semibold uppercase mb-2">Body State</h3>
          <div className="grid grid-cols-2 gap-1.5">
            {BODY_STATES.map((s) => (
              <button key={s} onClick={() => { setBodyState(s); if (s !== 'listening') setIsListening(false) }} className={btnCls(bodyState === s)}>
                {s}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 mt-2 text-gray-400 text-xs">
            <input type="checkbox" checked={isListening} onChange={(e) => { setIsListening(e.target.checked); if (e.target.checked) setBodyState('listening') }} className="rounded" />
            Listening mode
          </label>
        </section>

        <section>
          <h3 className="text-gray-400 text-xs font-semibold uppercase mb-2">Expression</h3>
          <div className="grid grid-cols-3 gap-1.5">
            {EMOTIONS.map((e) => (
              <button key={e.key} onClick={() => { setEmotion(e.key); getLipSyncController()?.setExpression(e.key) }} className={btnCls(emotion === e.key)}>
                {e.icon} {e.label}
              </button>
            ))}
          </div>
        </section>

        <section>
          <h3 className="text-gray-400 text-xs font-semibold uppercase mb-2">Gestures</h3>
          <div className="grid grid-cols-2 gap-1.5">
            {GESTURES.map((g) => (
              <button
                key={g}
                onClick={() => triggerGesture(g)}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all border ${
                  activeGesture === g
                    ? 'bg-purple-600 text-white border-purple-600'
                    : 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700'
                }`}
              >
                {gestureLabels[g] ?? g}
              </button>
            ))}
          </div>
        </section>

        <section>
          <h3 className="text-gray-400 text-xs font-semibold uppercase mb-2">Speaking</h3>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 bg-gray-900 text-white border border-gray-700 rounded-lg resize-none text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => getLipSyncController()?.speak(text)}
              disabled={!text.trim() || !connected}
              className="flex-1 h-8 bg-purple-600 text-white rounded-lg text-xs font-medium hover:bg-purple-500 disabled:opacity-30"
            >
              Speak (WS)
            </button>
          </div>
        </section>

        <section>
          <h3 className="text-gray-400 text-xs font-semibold uppercase mb-2">Status</h3>
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-yellow-500'}`} />
              <span className="text-gray-400">WebSocket: {connected ? 'Connected' : 'Connecting...'}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${speaking ? 'bg-purple-500' : 'bg-gray-600'}`} />
              <span className="text-gray-400">{speaking ? 'Speaking...' : 'Idle'}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${activeGesture ? 'bg-green-400' : 'bg-gray-600'}`} />
              <span className="text-gray-400">{activeGesture ? `Gesture: ${activeGesture}` : 'No gesture'}</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
