import { useEffect, useRef, useState } from 'react';
import { backoffMs } from './backoff';
import { useDocumentVisible } from './useDocumentVisible';

export const BLANK_PIXEL =
  'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';

export type StreamState = 'connecting' | 'live' | 'offline';

export interface MjpegPlayerProps {
  src?: string | null;
  label: string;
  subLabel?: string | null;
  hasCriticalAlert?: boolean;
  onStateChange?: (state: StreamState) => void;
  className?: string;
}

export function MjpegPlayer({
  src,
  label,
  subLabel,
  hasCriticalAlert = false,
  onStateChange,
  className = '',
}: MjpegPlayerProps) {
  const isDocumentVisible = useDocumentVisible();
  const imgRef = useRef<HTMLImageElement>(null);
  const [state, setState] = useState<StreamState>('connecting');
  const [attempt, setAttempt] = useState(0);
  const [retryIn, setRetryIn] = useState<number | null>(null);

  const updateState = (newState: StreamState) => {
    setState(newState);
    onStateChange?.(newState);
  };

  // Reconnection & connection management
  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;

    if (!src || !isDocumentVisible) {
      img.src = BLANK_PIXEL;
      updateState('offline');
      return;
    }

    updateState('connecting');
    const separator = src.includes('?') ? '&' : '?';
    img.src = `${src}${separator}_=${attempt}_${Date.now()}`;

    return () => {
      // Immediately sever the connection on unmount or URL swap
      img.src = BLANK_PIXEL;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src, attempt, isDocumentVisible]);

  // Backoff retry loop on stream drop
  useEffect(() => {
    if (state !== 'offline' || !isDocumentVisible || !src) {
      setRetryIn(null);
      return;
    }

    const delayMs = backoffMs(attempt);
    setRetryIn(Math.ceil(delayMs / 1000));

    const timer = setTimeout(() => {
      setAttempt((a) => a + 1);
    }, delayMs);

    return () => clearTimeout(timer);
  }, [state, attempt, isDocumentVisible, src]);

  return (
    <figure
      role="region"
      aria-label={`Live Video Stream ${label}`}
      className={`relative aspect-video bg-black rounded-[var(--radius)] overflow-hidden border ${
        hasCriticalAlert
          ? 'border-pulse-critical'
          : 'border-[var(--border)]'
      } ${className}`}
    >
      <img
        ref={imgRef}
        alt={`Live CCTV video feed from ${label}`}
        className="w-full h-full object-contain select-none"
        onLoad={() => {
          setAttempt(0);
          updateState('live');
        }}
        onError={() => {
          updateState('offline');
        }}
      />

      {/* Camera Header Overlay */}
      <figcaption className="absolute top-2 left-2 flex items-center gap-2 rounded bg-black/75 backdrop-blur-xs px-2.5 py-1 text-xs text-[var(--text)] select-none">
        <span
          className={`h-2 w-2 rounded-full ${
            state === 'live'
              ? 'bg-[var(--ok)] shadow-[0_0_8px_var(--ok)]'
              : state === 'connecting'
              ? 'bg-[var(--warn)] animate-pulse'
              : 'bg-[var(--offline)]'
          }`}
        />
        <span className="font-mono font-bold">{label}</span>
        {subLabel && <span className="text-[var(--text-muted)] truncate max-w-[140px]">· {subLabel}</span>}
      </figcaption>

      {/* Stream State Indicator Overlay */}
      <div className="absolute top-2 right-2 flex items-center gap-2 rounded bg-black/75 px-2 py-0.5 text-[11px] font-mono select-none">
        <span
          className={
            state === 'live'
              ? 'text-[var(--ok)]'
              : state === 'connecting'
              ? 'text-[var(--warn)]'
              : 'text-[var(--sev-critical)]'
          }
        >
          {state.toUpperCase()}
          {state === 'offline' && retryIn ? ` (~${retryIn}s)` : ''}
        </span>
      </div>

      {/* Offline Status Backdrop */}
      {state === 'offline' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 text-[var(--text-muted)] p-4 text-center">
          <div className="text-2xl mb-1">📹</div>
          <p className="text-xs font-semibold text-[var(--text)]">Stream Signal Offline</p>
          <p className="text-[11px] text-[var(--text-dim)] mt-0.5">
            {retryIn ? `Reconnecting in ~${retryIn}s (Attempt ${attempt + 1})...` : 'Waiting for connection...'}
          </p>
        </div>
      )}

      {/* AI Processing Watermark */}
      <div className="absolute bottom-1.5 right-2 text-[10px] text-[var(--text-dim)] font-mono select-none bg-black/60 px-1.5 py-0.5 rounded">
        AI PIPELINE ANNOTATED
      </div>
    </figure>
  );
}
