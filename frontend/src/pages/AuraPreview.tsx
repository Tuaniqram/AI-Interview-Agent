import { useState, useEffect, useCallback } from 'react';
import { AuraCore } from '../components/AuraCore';
import type { AuraState } from '../components/AuraCore';

const STATES: AuraState[] = ['idle', 'listening', 'thinking', 'responding'];
const LABELS: Record<AuraState, string> = {
  idle: 'Idle',
  listening: 'Listening',
  thinking: 'Thinking',
  responding: 'Responding',
};

export function AuraPreview() {
  const [state, setState] = useState<AuraState>('idle');
  const [autoCycle, setAutoCycle] = useState(false);

  const cycle = useCallback(() => {
    setState(prev => {
      const idx = STATES.indexOf(prev);
      return STATES[(idx + 1) % STATES.length];
    });
  }, []);

  useEffect(() => {
    if (!autoCycle) return;
    const id = setInterval(cycle, 3000);
    return () => clearInterval(id);
  }, [autoCycle, cycle]);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: '#050816',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      fontFamily: "'Inter', system-ui, sans-serif",
      color: '#c8cdd8',
    }}>
      {/* Title */}
      <div style={{ marginBottom: 32, textAlign: 'center' }}>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11, letterSpacing: '0.1em',
          color: '#5a6272', textTransform: 'uppercase',
          marginBottom: 8,
        }}>
          A.U.R.A Core — Preview
        </div>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12, color: '#7C5CFF',
          letterSpacing: '0.05em',
        }}>
          {LABELS[state]}
        </div>
      </div>

      {/* Core */}
      <AuraCore state={state} size={360} />

      {/* Controls */}
      <div style={{ display: 'flex', gap: 10, marginTop: 40, alignItems: 'center' }}>
        {STATES.map(s => (
          <button
            key={s}
            onClick={() => { setAutoCycle(false); setState(s); }}
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11, letterSpacing: '0.06em',
              padding: '10px 20px', borderRadius: 8,
              background: state === s && !autoCycle ? 'rgba(124,92,255,0.15)' : 'rgba(255,255,255,0.03)',
              border: `1px solid ${state === s && !autoCycle ? '#7C5CFF' : 'rgba(255,255,255,0.06)'}`,
              color: state === s && !autoCycle ? '#fff' : '#5a6272',
              cursor: 'pointer',
              transition: 'all 0.25s',
              textTransform: 'uppercase',
            }}
          >
            {LABELS[s]}
          </button>
        ))}

        <div style={{ width: 1, height: 24, background: 'rgba(255,255,255,0.06)', margin: '0 4px' }} />

        <button
          onClick={() => setAutoCycle(prev => !prev)}
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11, letterSpacing: '0.06em',
            padding: '10px 20px', borderRadius: 8,
            background: autoCycle ? 'rgba(93,228,255,0.12)' : 'rgba(255,255,255,0.03)',
            border: `1px solid ${autoCycle ? '#5DE4FF' : 'rgba(255,255,255,0.06)'}`,
            color: autoCycle ? '#5DE4FF' : '#5a6272',
            cursor: 'pointer',
            transition: 'all 0.25s',
            textTransform: 'uppercase',
          }}
        >
          {autoCycle ? 'Stop' : 'Auto-cycle'}
        </button>
      </div>

      {/* Footer hint */}
      <div style={{
        position: 'fixed', bottom: 20,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10, color: '#3a4050',
        letterSpacing: '0.05em',
      }}>
        /aura-preview — temporary route, will be removed after approval
      </div>
    </div>
  );
}
