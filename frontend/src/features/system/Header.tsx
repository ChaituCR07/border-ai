import { useUIStore } from '../../state/uiStore';
import { Clock } from './Clock';
import { ConnectionBadge } from './ConnectionBadge';

export function Header() {
  const videoLayout = useUIStore((s) => s.videoLayout);
  const toggleVideoLayout = useUIStore((s) => s.toggleVideoLayout);

  return (
    <header className="h-14 border-b border-[var(--border)] bg-[var(--bg-panel)] px-4 flex items-center justify-between select-none">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--ok)] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-[var(--ok)]"></span>
          </span>
          <h1 className="text-sm sm:text-base font-bold tracking-wider uppercase text-[var(--text)]">
            Border AI <span className="text-[var(--text-muted)] font-normal">Command Center</span>
          </h1>
        </div>
        <span className="hidden md:inline text-xs px-2 py-0.5 rounded bg-[var(--border-muted)] text-[var(--text-muted)] font-mono">
          v0.3.0
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={toggleVideoLayout}
          aria-label={`Toggle video grid layout. Current layout is ${videoLayout}`}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-xs border border-[var(--border)] bg-[var(--bg-panel-2)] hover:bg-[var(--bg-panel-hover)] cursor-pointer transition-colors font-medium text-[var(--text)]"
        >
          <span className="text-[var(--text-muted)] font-mono">GRID:</span>
          <span className="font-bold text-[var(--sev-low)]">{videoLayout.toUpperCase()}</span>
        </button>

        <Clock />
        <ConnectionBadge />
      </div>
    </header>
  );
}
