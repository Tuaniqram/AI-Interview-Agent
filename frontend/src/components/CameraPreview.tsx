import React from 'react';
import { Camera, CameraOff } from 'lucide-react';

interface CameraPreviewProps {
  stream: MediaStream | null;
  isCameraOn: boolean;
  onToggle: () => void;
  size?: 'sm' | 'md' | 'lg';
}

export function CameraPreview({ stream, isCameraOn, onToggle, size = 'md' }: CameraPreviewProps) {
  const videoRef = React.useRef<HTMLVideoElement>(null);

  React.useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  const sizeClass = size === 'sm' ? 'w-24 h-24' : size === 'lg' ? 'w-40 h-40' : 'w-32 h-32';

  return (
    <div className={`relative ${sizeClass} rounded-full overflow-hidden border-2 border-purple-300 bg-gray-900`}>
      {isCameraOn && stream ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover scale-x-[-1]"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-gray-800">
          <CameraOff className="w-8 h-8 text-gray-500" />
        </div>
      )}
      <button
        onClick={onToggle}
        className="absolute bottom-0 right-0 w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center hover:bg-purple-700 transition-colors shadow-lg"
        title={isCameraOn ? 'Turn off camera' : 'Turn on camera'}
      >
        {isCameraOn ? (
          <Camera className="w-4 h-4 text-white" />
        ) : (
          <CameraOff className="w-4 h-4 text-white" />
        )}
      </button>
    </div>
  );
}
