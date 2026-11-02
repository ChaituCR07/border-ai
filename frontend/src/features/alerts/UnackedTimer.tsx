import React, { useEffect, useState } from 'react';
import { usePublicConfig } from './usePublicConfig';

interface UnackedTimerProps {
  createdAt: string;
  status: string;
  criticalAfterSeconds?: number;
  className?: string;
}

export function formatElapsed(seconds: number): string {
  if (seconds < 60) {
    return `${Math.max(0, seconds)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins < 60) {
    return `${mins}m ${secs}s`;
  }
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  return `${hours}h ${remMins}m`;
}

export const UnackedTimer: React.FC<UnackedTimerProps> = ({
  createdAt,
  status,
  criticalAfterSeconds,
  className = '',
}) => {
  const { data: config } = usePublicConfig();
  const threshold = criticalAfterSeconds ?? config?.escalation?.critical_after_s ?? 300;

  const [elapsedSeconds, setElapsedSeconds] = useState<number>(() => {
    const createdMs = new Date(createdAt).getTime();
    return Math.max(0, Math.floor((Date.now() - createdMs) / 1000));
  });

  useEffect(() => {
    if (status !== 'OPEN') return;

    const update = () => {
      const createdMs = new Date(createdAt).getTime();
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - createdMs) / 1000)));
    };

    update();
    const interval = setInterval(update, 15_000); // 15s ticker
    return () => clearInterval(interval);
  }, [createdAt, status]);

  if (status !== 'OPEN') {
    return null;
  }

  const isEscalated = elapsedSeconds >= threshold;
  const isApproaching = elapsedSeconds >= threshold / 2 && !isEscalated;

  let badgeStyle = 'text-[var(--text-dim)] bg-transparent border-transparent';
  let prefix = '⏱';

  if (isEscalated) {
    badgeStyle = 'bg-rose-950/80 text-rose-300 border-rose-600/80 font-bold animate-pulse';
    prefix = '🚨 Escalated';
  } else if (isApproaching) {
    badgeStyle = 'bg-amber-950/70 text-amber-300 border-amber-600/70 font-semibold';
    prefix = '⚠️ Approaching';
  }

  return (
    <span
      role="timer"
      aria-label={`Unacknowledged for ${formatElapsed(elapsedSeconds)}`}
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono border ${badgeStyle} ${className}`}
      title={`Created at ${createdAt} (${threshold}s escalation threshold)`}
    >
      <span>{prefix}</span>
      <span>{formatElapsed(elapsedSeconds)}</span>
    </span>
  );
};
