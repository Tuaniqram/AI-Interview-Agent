import { getLipSyncController } from '../AvatarRenderer';
import type { AvatarEmotion } from '../../types/avatar';

export const BODY_STATES = ['idle', 'speaking', 'listening', 'thinking'] as const;
export type BodyState = typeof BODY_STATES[number];

export const EMOTIONS: { key: AvatarEmotion; label: string }[] = [
  { key: 'neutral', label: 'Neutral' },
  { key: 'laughing', label: 'Laughing' },
  { key: 'considering', label: 'Considering' },
  { key: 'excited', label: 'Excited' },
  { key: 'thoughtful', label: 'Thoughtful' },
];

export const GESTURES = [
  'openPalm', 'singleHandEmphasis', 'bothHandsOpen', 'forearmLift',
  'palmUpward', 'smallPointing', 'shoulderEmphasis', 'chestEmphasis',
  'fingerEmphasis', 'handRotation', 'smallShrug', 'questionEmphasis',
  'agreementNod', 'explanationGesture', 'closingGesture',
] as const;

function btnCls(active: boolean): string {
  return `px-3 py-1.5 text-xs rounded-lg font-medium transition-all  ${active ? 'bg-action-primary text-inverse' : 'bg-input text-secondary hover:bg-hover'}`;
}

const gestureLabels: Record<string, string> = {
  openPalm: 'Open Palm', singleHandEmphasis: 'Single Hand', bothHandsOpen: 'Both Hands',
  forearmLift: 'Forearm Lift', palmUpward: 'Palm Up', smallPointing: 'Point',
  shoulderEmphasis: 'Shoulder', chestEmphasis: 'Chest', fingerEmphasis: 'Finger',
  handRotation: 'Hand Rotate', smallShrug: 'Shrug', questionEmphasis: 'Question',
  agreementNod: 'Nod', explanationGesture: 'Explain', closingGesture: 'Closing',
};

interface AnimationControlsProps {
  bodyState: BodyState;
  onBodyStateChange: (s: BodyState) => void;
  emotion: AvatarEmotion;
  onEmotionChange: (e: AvatarEmotion) => void;
  isListening: boolean;
  onListeningChange: (v: boolean) => void;
  activeGesture: string | null;
  onTriggerGesture: (g: string) => void;
  onStopGesture: () => void;
  text: string;
  onTextChange: (t: string) => void;
  onSpeak: () => void;
  connected: boolean;
  speaking: boolean;
  debugMode: boolean;
  onDebugModeChange: (v: boolean) => void;
  debugInfo: string;
}

export function AnimationControls({
  bodyState, onBodyStateChange, emotion, onEmotionChange,
  isListening, onListeningChange, activeGesture, onTriggerGesture, onStopGesture,
  text, onTextChange, onSpeak, connected, speaking, debugMode, onDebugModeChange, debugInfo,
}: AnimationControlsProps) {
  return (
    <div className="w-80 bg-section overflow-y-auto p-4 space-y-5">
      <h2 className="text-primary font-bold text-sm tracking-wide">Animation Controls</h2>

      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-secondary text-xs font-semibold uppercase">Debug</h3>
          <label className="flex items-center gap-1.5 text-secondary text-xs cursor-pointer">
            <input type="checkbox" checked={debugMode} onChange={e => onDebugModeChange(e.target.checked)} className="rounded" />
            Gesture Debug
          </label>
        </div>
        <div className="flex gap-1.5">
          <button onClick={onStopGesture} disabled={!activeGesture}
            className="flex-1 px-2 py-1.5 text-xs rounded-lg font-medium bg-action-danger text-action-danger-text hover:bg-action-danger-hover disabled:opacity-30 disabled:cursor-not-allowed">
            Stop Gesture
          </button>
        </div>
      </section>

      <section>
        <h3 className="text-secondary text-xs font-semibold uppercase mb-2">Body State</h3>
        <div className="grid grid-cols-2 gap-1.5">
          {BODY_STATES.map(s => (
            <button key={s} onClick={() => { onBodyStateChange(s); if (s !== 'listening') onListeningChange(false); }} className={btnCls(bodyState === s)}>
              {s}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 mt-2 text-secondary text-xs">
          <input type="checkbox" checked={isListening} onChange={e => { onListeningChange(e.target.checked); if (e.target.checked) onBodyStateChange('listening'); }} className="rounded" />
          Listening mode
        </label>
      </section>

      <section>
        <h3 className="text-secondary text-xs font-semibold uppercase mb-2">Expression</h3>
        <div className="grid grid-cols-3 gap-1.5">
          {EMOTIONS.map(e => (
            <button key={e.key} onClick={() => { onEmotionChange(e.key); getLipSyncController()?.setExpression(e.key); }} className={btnCls(emotion === e.key)}>
              {e.label}
            </button>
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-secondary text-xs font-semibold uppercase mb-2">Gestures</h3>
        <div className="grid grid-cols-2 gap-1.5">
          {GESTURES.map(g => (
            <button key={g} onClick={() => onTriggerGesture(g)}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all  ${activeGesture === g ? 'bg-action-primary text-inverse' : 'bg-input text-secondary hover:bg-hover'}`}>
              {gestureLabels[g] ?? g}
            </button>
          ))}
        </div>
      </section>

      <section>
        <h3 className="text-secondary text-xs font-semibold uppercase mb-2">Speaking</h3>
        <textarea value={text} onChange={e => onTextChange(e.target.value)} rows={2}
          className="w-full px-3 py-2 bg-input text-primary rounded-lg resize-none text-xs focus:outline-none focus:ring-1 focus:ring-focus" />
        <div className="flex gap-2 mt-2">
          <button onClick={onSpeak} disabled={!text.trim() || !connected}
            className="flex-1 h-8 bg-action-primary text-inverse rounded-lg text-xs font-medium hover:bg-action-primary-hover disabled:opacity-30">
            Speak (WS)
          </button>
        </div>
      </section>

      <section>
        <h3 className="text-secondary text-xs font-semibold uppercase mb-2">Status</h3>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-success' : 'bg-warning'}`} />
            <span className="text-secondary">WebSocket: {connected ? 'Connected' : 'Connecting...'}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${speaking ? 'bg-action-primary' : 'bg-muted'}`} />
            <span className="text-secondary">{speaking ? 'Speaking...' : 'Idle'}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${activeGesture ? 'bg-success' : 'bg-muted'}`} />
            <span className="text-secondary">{activeGesture ? `Gesture: ${activeGesture}` : 'No gesture'}</span>
          </div>
          {debugMode && (
            <pre className="mt-2 bg-overlay text-success text-[10px] font-mono p-2 rounded whitespace-pre leading-tight">
              {debugInfo}
            </pre>
          )}
        </div>
      </section>
    </div>
  );
}
