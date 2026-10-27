import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { AlertView } from '@border-ai/protocol';
import { LiveSocket, type SocketStatus, type ResyncReason } from './LiveSocket';
import { applyAlertMessage, type AlertMessage } from './applyAlertMessage';
import { enqueue, dismissById, expire, type Toast } from './toastQueue';
import { playAlertSound, unlockAudio, isAudioUnlocked, isAudioMuted, setAudioMuted } from './alertSound';
import { AlertToastStack } from './AlertToastStack';

export type TransportType = 'websocket' | 'polling';

interface LiveAlertsContextValue {
  transport: TransportType;
  socketStatus: SocketStatus;
  toasts: Toast[];
  dismissToast: (id: string) => void;
  resyncBannerCount: number | null;
  clearResyncBanner: () => void;
  isAudioUnlocked: boolean;
  isAudioMuted: boolean;
  enableAudio: () => Promise<boolean>;
  toggleMute: () => void;
}

const LiveAlertsContext = createContext<LiveAlertsContextValue | null>(null);

export function useLiveAlertsContext(): LiveAlertsContextValue {
  const ctx = useContext(LiveAlertsContext);
  if (!ctx) {
    throw new Error('useLiveAlertsContext must be used within a LiveAlertsProvider');
  }
  return ctx;
}

interface LiveAlertsProviderProps {
  children: React.ReactNode;
  wsUrl?: string;
  disableAutoConnect?: boolean;
}

export function LiveAlertsProvider({
  children,
  wsUrl,
  disableAutoConnect = false,
}: LiveAlertsProviderProps) {
  const queryClient = useQueryClient();
  const [socketStatus, setSocketStatus] = useState<SocketStatus>('closed');
  const [consecutiveFailures, setConsecutiveFailures] = useState(0);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [resyncBannerCount, setResyncBannerCount] = useState<number | null>(null);
  const [audioUnlocked, setAudioUnlocked] = useState(false);
  const [muted, setMutedState] = useState(isAudioMuted());

  const resyncingRef = useRef(false);
  const bufferRef = useRef<AlertMessage[]>([]);
  const socketRef = useRef<LiveSocket | null>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hiddenTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced counter invalidation (ADR 0020 / Task 7)
  const scheduleCounterRefresh = useCallback(() => {
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: ['analytics', 'threats'] });
      queryClient.invalidateQueries({ queryKey: ['analytics', 'cameras'] });
    }, 500);
  }, [queryClient]);

  // Handle incoming live alert delta
  const handleLiveMessage = useCallback(
    (msg: AlertMessage) => {
      if (resyncingRef.current) {
        // Delta arrived during in-flight resync: buffer it to avoid snapshot overwriting
        bufferRef.current.push(msg);
        return;
      }

      // Read current cache
      const currentAlerts = queryClient.getQueryData<AlertView[]>(['alerts', 'open', 'all']) ?? [];
      const isNewAlert =
        msg.type === 'alert.created' &&
        !currentAlerts.some((a) => a.alert_id === msg.data.alert.alert_id);

      // Update React Query cache
      queryClient.setQueryData<AlertView[]>(['alerts', 'open', 'all'], (old = []) =>
        applyAlertMessage(old, msg)
      );

      // Trigger debounced threat counter update
      scheduleCounterRefresh();

      // Trigger Toast & Audio for new live created alert (not during resync)
      if (isNewAlert && msg.type === 'alert.created') {
        const alert = msg.data.alert;
        setToasts((prev) => enqueue(prev, alert, Date.now()));
        if (alert.priority === 'CRITICAL' || alert.priority === 'HIGH') {
          playAlertSound(alert.priority);
        }
      }
    },
    [queryClient, scheduleCounterRefresh]
  );

  // Handle resync
  const handleResync = useCallback(
    async (reason: ResyncReason) => {
      resyncingRef.current = true;

      const previousCount =
        queryClient.getQueryData<AlertView[]>(['alerts', 'open', 'all'])?.length ?? 0;

      try {
        // Refetch full open alerts list and threats
        await queryClient.refetchQueries({ queryKey: ['alerts', 'open', 'all'] });
        await queryClient.refetchQueries({ queryKey: ['analytics', 'threats'] });

        // Apply any deltas buffered while refetch was in-flight
        if (bufferRef.current.length > 0) {
          queryClient.setQueryData<AlertView[]>(['alerts', 'open', 'all'], (old = []) => {
            let updated = old;
            for (const delta of bufferRef.current) {
              updated = applyAlertMessage(updated, delta);
            }
            return updated;
          });
          bufferRef.current = [];
        }

        // Show offline banner if new alerts arrived during disconnect
        const newCount =
          queryClient.getQueryData<AlertView[]>(['alerts', 'open', 'all'])?.length ?? 0;
        if (reason !== 'connected' && newCount > previousCount) {
          setResyncBannerCount(newCount - previousCount);
        }
      } finally {
        resyncingRef.current = false;
      }
    },
    [queryClient]
  );

  // Toast expiration interval
  useEffect(() => {
    const timer = setInterval(() => {
      setToasts((prev) => expire(prev, Date.now()));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Update document title with critical alert indicator
  useEffect(() => {
    const criticalCount = toasts.filter((t) => t.alert.priority === 'CRITICAL').length;
    if (criticalCount > 0) {
      document.title = `(${criticalCount}) 🚨 Border AI Command Center`;
    } else {
      document.title = 'Border AI Command Center';
    }
  }, [toasts]);

  // Tab visibility: disconnect after 5 minutes hidden to save connections
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        hiddenTimerRef.current = setTimeout(() => {
          socketRef.current?.stop();
        }, 5 * 60 * 1000);
      } else {
        if (hiddenTimerRef.current) {
          clearTimeout(hiddenTimerRef.current);
          hiddenTimerRef.current = null;
        }
        if (socketRef.current) {
          socketRef.current.start();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (hiddenTimerRef.current) clearTimeout(hiddenTimerRef.current);
    };
  }, []);

  // Initialize socket
  useEffect(() => {
    if (disableAutoConnect) return;

    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' ? window.location.host : 'localhost:4000';
    const targetUrl = wsUrl ?? `${protocol}//${host}/api/ws`;

    const socket = new LiveSocket({
      url: targetUrl,
      onStatus: (status) => {
        setSocketStatus(status);
        if (status === 'open') {
          setConsecutiveFailures(0);
        } else if (status === 'closed') {
          setConsecutiveFailures((f) => f + 1);
        }
      },
      onMessage: handleLiveMessage,
      onResync: handleResync,
    });

    socketRef.current = socket;
    socket.start();

    return () => {
      socket.stop();
      socketRef.current = null;
    };
  }, [disableAutoConnect, wsUrl, handleLiveMessage, handleResync]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => dismissById(prev, id));
  }, []);

  const enableAudio = useCallback(async () => {
    const ok = await unlockAudio();
    setAudioUnlocked(ok);
    return ok;
  }, []);

  const toggleMute = useCallback(() => {
    const next = !isAudioMuted();
    setAudioMuted(next);
    setMutedState(next);
  }, []);

  // Transport state logic (Task 7):
  // websocket only while socket is open and healthy; polling in every other state or >=3 failures
  const transport: TransportType =
    socketStatus === 'open' && consecutiveFailures < 3 ? 'websocket' : 'polling';

  return (
    <LiveAlertsContext.Provider
      value={{
        transport,
        socketStatus,
        toasts,
        dismissToast,
        resyncBannerCount,
        clearResyncBanner: () => setResyncBannerCount(null),
        isAudioUnlocked: audioUnlocked,
        isAudioMuted: muted,
        enableAudio,
        toggleMute,
      }}
    >
      {children}
      <AlertToastStack toasts={toasts} onDismiss={dismissToast} />
    </LiveAlertsContext.Provider>
  );
}
