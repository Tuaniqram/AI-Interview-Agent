import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { AvatarRenderer, getLipSyncController } from '../components/AvatarRenderer';
import { AnimationControls, BodyState } from '../components/avatar-lab/AnimationControls';
import type { AvatarEmotion } from '../types/avatar';

export function AvatarLab() {
  const navigate = useNavigate();
  const [bodyState, setBodyState] = React.useState<BodyState>('idle');
  const [emotion, setEmotion] = React.useState<AvatarEmotion>('neutral');
  const [isListening, setIsListening] = React.useState(false);
  const [connected, setConnected] = React.useState(false);
  const [speaking, setSpeaking] = React.useState(false);
  const [text, setText] = React.useState('Hello, I am your AI interviewer.');
  const [debugMode, setDebugMode] = React.useState(false);
  const [activeGesture, setActiveGesture] = React.useState<string | null>(null);
  const [debugInfo, setDebugInfo] = React.useState('No gesture active');

  React.useEffect(() => {
    const prev = document.documentElement.getAttribute('data-theme') || 'light';
    document.documentElement.setAttribute('data-theme', 'dark');
    return () => {
      document.documentElement.setAttribute('data-theme', prev);
    };
  }, []);

  // ESC key to go back
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') navigate('/');
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  React.useEffect(() => {
    const id = setInterval(() => {
      const lc = getLipSyncController();
      if (lc) {
        clearInterval(id);
        lc.connect('anim-lab-session', import.meta.env.VITE_API_BASE_URL || 'localhost:8000');
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
          `Gesture: ${debug.gesture}\nState: ${debug.state}\nProgress: ${debug.progress.toFixed(2)}\nPhase: ${debug.phaseIndex}\nElapsed: ${debug.elapsed.toFixed(2)}s\nBones: ${rotStr}`
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
      if (lc.hasActiveGesture()) lc.stopGesture();
      lc.triggerGesture(g as any);
    }
  };

  const stopCurrentGesture = () => getLipSyncController()?.stopGesture();
  const effectiveSpeaking = speaking || bodyState === 'speaking';

  return (
    <div className="fixed inset-0 bg-page flex">
      {/* Floating back button */}
      <button
        onClick={() => navigate('/')}
        className="fixed top-4 left-4 z-50 flex items-center gap-2 px-3 py-2 bg-overlay/80 backdrop-blur-sm text-secondary hover:text-primary rounded-lg border border-default hover:border-strong transition-all opacity-60 hover:opacity-100"
      >
        <ArrowLeft className="w-4 h-4" />
        <span className="text-xs font-medium">Back</span>
        <kbd className="ml-1 text-[10px] text-muted bg-hover px-1.5 py-0.5 rounded border border-default">ESC</kbd>
      </button>

      <div className="flex-1 relative">
        <AvatarRenderer
          emotion={emotion}
          activeViseme={null}
          isSpeaking={effectiveSpeaking}
          isListening={isListening}
          className="w-full h-full"
        />
      </div>

      <AnimationControls
        bodyState={bodyState}
        onBodyStateChange={setBodyState}
        emotion={emotion}
        onEmotionChange={setEmotion}
        isListening={isListening}
        onListeningChange={setIsListening}
        activeGesture={activeGesture}
        onTriggerGesture={triggerGesture}
        onStopGesture={stopCurrentGesture}
        text={text}
        onTextChange={setText}
        onSpeak={() => getLipSyncController()?.speak(text)}
        connected={connected}
        speaking={speaking}
        debugMode={debugMode}
        onDebugModeChange={setDebugMode}
        debugInfo={debugInfo}
      />
    </div>
  );
}
