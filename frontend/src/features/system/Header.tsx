import { Link } from 'react-router-dom';
import { useUIStore } from '../../state/uiStore';
import { Clock } from './Clock';
import { ConnectionBadge } from './ConnectionBadge';
import { useLiveAlertsContext } from '../alerts/LiveAlertsProvider';

export function Header() {
  const videoLayout = useUIStore((s) => s.videoLayout);
  const toggleVideoLayout = useUIStore((s) => s.toggleVideoLayout);

  let isAudioUnlocked = false;
  let isAudioMuted = false;
  let enableAudio = async () => false;
  let toggleMute = () => {};

  try {
    const live = useLiveAlertsContext();
    isAudioUnlocked = live.isAudioUnlocked;
    isAudioMuted = live.isAudioMuted;
    enableAudio = live.enableAudio;
    toggleMute = live.toggleMute;
  } catch {
    // Context fallback
  }

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
        {/* Web Audio Alert Tone Controls (ADR 0021) */}
        {!isAudioUnlocked ? (
          <button
            type="button"
            onClick={enableAudio}
            title="Click to enable alert chime audio"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs border border-[var(--border)] bg-[var(--bg-panel-2)] hover:bg-[var(--bg-panel-hover)] text-[var(--text-muted)] hover:text-[var(--text)] transition-colors cursor-pointer"
          >
            <span>🔔</span>
            <span className="font-semibold text-[11px]">Enable Sound</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={toggleMute}
            title={isAudioMuted ? 'Alert sounds muted - click to unmute' : 'Alert sounds active - click to mute'}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs border transition-colors cursor-pointer ${
              isAudioMuted
                ? 'border-[var(--warn)] bg-[var(--warn-bg)] text-[var(--warn)]'
                : 'border-[var(--border)] bg-[var(--bg-panel-2)] text-[var(--ok)]'
            }`}
          >
            <span>{isAudioMuted ? '🔕' : '🔔'}</span>
            <span className="font-semibold text-[11px]">{isAudioMuted ? 'Muted' : 'Sound ON'}</span>
          </button>
        )}

        <button
          onClick={toggleVideoLayout}
          aria-label={`Toggle video grid layout. Current layout is ${videoLayout}`}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-xs border border-[var(--border)] bg-[var(--bg-panel-2)] hover:bg-[var(--bg-panel-hover)] cursor-pointer transition-colors font-medium text-[var(--text)]"
        >
          <span className="text-[var(--text-muted)] font-mono">GRID:</span>
          <span className="font-bold text-[var(--sev-low)]">{videoLayout.toUpperCase()}</span>
        </button>

        <Link
          to="/investigation"
          aria-label="Open forensic investigation workbench"
          className="flex items-center gap-1.5 px-3 py-1 rounded text-xs border border-sky-800/60 bg-sky-950/60 hover:bg-sky-900/60 text-sky-200 transition-colors font-medium cursor-pointer"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <span>Investigation</span>
          <kbd className="hidden sm:inline-block px-1 py-0.2 text-[10px] bg-sky-900/80 rounded border border-sky-700/60">
            /
          </kbd>
        </Link>

        <Clock />
        <ConnectionBadge />
      </div>
    </header>
  );
}
