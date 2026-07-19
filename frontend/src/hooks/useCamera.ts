import { useState, useCallback, useRef, useEffect } from 'react';

export interface CameraState {
  isCameraOn: boolean;
  stream: MediaStream | null;
  error: string | null;
  isPermissionDenied: boolean;
}

export function useCamera() {
  const [state, setState] = useState<CameraState>({
    isCameraOn: false,
    stream: null,
    error: null,
    isPermissionDenied: false,
  });
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    return () => {
      stopMediaStream(streamRef.current);
    };
  }, []);

  const startCamera = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, error: null }));
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 320 },
          height: { ideal: 240 },
          facingMode: 'user',
        },
        audio: false,
      });
      streamRef.current = stream;
      setState({
        isCameraOn: true,
        stream,
        error: null,
        isPermissionDenied: false,
      });
    } catch (err: unknown) {
      const msg = err instanceof DOMException && err.name === 'NotAllowedError'
        ? 'Camera permission denied'
        : 'Camera error: ' + (err instanceof Error ? err.message : String(err));
      setState({
        isCameraOn: false,
        stream: null,
        error: msg,
        isPermissionDenied: err instanceof DOMException && err.name === 'NotAllowedError',
      });
    }
  }, []);

  const stopCamera = useCallback(() => {
    stopMediaStream(streamRef.current);
    streamRef.current = null;
    setState({
      isCameraOn: false,
      stream: null,
      error: null,
      isPermissionDenied: false,
    });
  }, []);

  return {
    ...state,
    startCamera,
    stopCamera,
  };
}

function stopMediaStream(stream: MediaStream | null) {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
  }
}
