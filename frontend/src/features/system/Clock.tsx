import { useEffect, useState } from 'react';
import { useUIStore } from '../../state/uiStore';

export function Clock() {
  const [now, setNow] = useState(() => new Date());
  const tzMode = useUIStore((s) => s.tzMode);
  const toggleTzMode = useUIStore((s) => s.toggleTzMode);

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const timeStr = now.toLocaleTimeString('en-GB', {
    hour12: false,
    timeZone: tzMode === 'UTC' ? 'UTC' : undefined,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const dateStr = now.toLocaleDateString('en-GB', {
    timeZone: tzMode === 'UTC' ? 'UTC' : undefined,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });

  return (
    <button
      onClick={toggleTzMode}
      title="Click to toggle UTC / Local timezone"
      aria-label={`System clock: ${timeStr} ${tzMode}, click to toggle timezone`}
      className="flex items-center gap-2 px-3 py-1 rounded bg-[var(--bg-panel)] hover:bg-[var(--bg-panel-hover)] border border-[var(--border)] text-xs text-[var(--text-muted)] cursor-pointer transition-colors"
    >
      <span className="font-mono font-medium text-[var(--text)]">{timeStr}</span>
      <span className="text-[10px] uppercase font-bold text-[var(--sev-low)]">{tzMode}</span>
      <span className="hidden sm:inline text-[var(--text-dim)]">· {dateStr}</span>
    </button>
  );
}
