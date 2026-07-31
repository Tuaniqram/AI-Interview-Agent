import { useEffect, useState } from 'react';

export interface WaveformData {
  timestamp: number;
  confidence: number;
}

interface VoiceWaveformProps {
  isListening?: boolean;
  data?: WaveformData[];
  className?: string;
}

export function VoiceWaveform({
  isListening = false,
  data = [],
  className = ''
}: VoiceWaveformProps) {
  const [bars, setBars] = useState(Array(32).fill(0));

  useEffect(() => {
    if (isListening && data.length > 0) {
      const interval = setInterval(() => {
        const newData = data.map(() => Math.random());
        setBars(newData);
      }, 50);
      return () => clearInterval(interval);
    } else if (!isListening) {
      const interval = setInterval(() => {
        setBars(prev => prev.map(bar => Math.max(0, bar * 0.95)));
      }, 30);
      return () => clearInterval(interval);
    }
  }, [isListening, data]);

  return (
    <div className={`flex items-center justify-center gap-px ${className} ${isListening ? '' : 'opacity-0'}`}>
      {bars.map((height, index) => (
        <div
          key={index}
          className="w-[3px] rounded-full"
          style={{
            height: `${8 + height * 24}px`,
            background: `linear-gradient(to top, var(--action-primary), #a78bfa)`,
            opacity: isListening ? 1 : Math.max(0, height),
            transition: isListening ? 'height 50ms ease-out' : 'height 300ms ease-out, opacity 300ms ease-out',
          }}
        />
      ))}
    </div>
  );
}
