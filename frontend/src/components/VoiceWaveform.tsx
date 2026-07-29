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
      // Animate bars going down
      const interval = setInterval(() => {
        setBars(bars.map(bar => Math.max(0, bar * 0.95)));
      }, 30);
      
      return () => clearInterval(interval);
    }
  }, [isListening, data]);

  const maxBarHeight = 100;

  return (
    <div className={`flex items-center justify-center gap-1 ${className}`}>
      {bars.map((height, index) => (
        <div
          key={index}
          className="w-1.5 rounded-full transition-all duration-75"
          style={{
            height: `${height * maxBarHeight}%`,
            backgroundColor: isListening 
              ? `linear-gradient(to top, #8b6ff5, #a78bfa)`
              : '#2d2d32',
            minHeight: '4px',
            transition: isListening ? 'height 50ms ease-out' : 'height 300ms ease-out',
          }}
        />
      ))}
    </div>
  );
}