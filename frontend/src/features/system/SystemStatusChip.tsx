import { useEffect, useState } from 'react';

interface ComponentHealth {
  ok: boolean;
  latency_ms?: number;
  build?: string;
  device?: string;
  age_s?: number;
  lag?: number;
  pending?: number;
  dead_stream_len?: number;
  clients?: number;
  seq?: number;
  queue_oldest_age_s?: number;
  smtp_ok?: boolean;
}

interface CameraStatus {
  camera_id: string;
  state: 'ONLINE' | 'STALLED' | 'RECONNECTING' | 'OFFLINE';
  fps?: number;
  last_frame_at?: string;
  reconnects?: number;
}

interface SystemStatusResponse {
  data: {
    status: 'OK' | 'DEGRADED' | 'DOWN';
    components: Record<string, ComponentHealth>;
    cameras: CameraStatus[];
  };
}

export function SystemStatusChip() {
  const [data, setData] = useState<SystemStatusResponse['data'] | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isStale, setIsStale] = useState(false);

  useEffect(() => {
    let active = true;

    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/system/status', {
          headers: { Accept: 'application/json' },
        });
        if (!active) return;
        if (res.ok) {
          const json: SystemStatusResponse = await res.json();
          setData(json.data);
          setIsStale(false);
        } else {
          setIsStale(true);
        }
      } catch {
        if (active) setIsStale(true);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const overall = isStale ? 'DEGRADED' : data?.status || 'OK';

  const badgeColors = {
    OK: 'bg-emerald-950/80 text-emerald-300 border-emerald-600/40 hover:bg-emerald-900/80',
    DEGRADED: 'bg-amber-950/80 text-amber-300 border-amber-600/40 hover:bg-amber-900/80',
    DOWN: 'bg-red-950/80 text-red-300 border-red-600/40 hover:bg-red-900/80',
  };

  const dotColors = {
    OK: 'bg-emerald-400',
    DEGRADED: 'bg-amber-400 animate-pulse',
    DOWN: 'bg-red-500 animate-ping',
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        title="Click to view comprehensive system telemetry and component health"
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs border font-mono transition-colors cursor-pointer ${badgeColors[overall]}`}
      >
        <span className={`inline-block h-2 w-2 rounded-full ${dotColors[overall]}`} />
        <span className="font-semibold">{isStale ? 'STALE' : overall}</span>
      </button>

      {isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="w-full max-w-xl bg-[var(--bg-panel)] border border-[var(--border)] rounded-[var(--radius)] shadow-2xl p-5 space-y-4 max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
              <div className="flex items-center gap-2">
                <span className={`h-3 w-3 rounded-full ${dotColors[overall]}`} />
                <h3 className="font-bold text-sm tracking-wide text-[var(--text)]">
                  System Health & Component Status
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text)] text-sm px-2 py-1 rounded"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <h4 className="font-bold text-[var(--text-dim)] uppercase tracking-wider text-[10px]">
                Core Components
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {data &&
                  Object.entries(data.components).map(([name, comp]) => (
                    <div
                      key={name}
                      className="p-2.5 rounded bg-[var(--bg-panel-2)] border border-[var(--border-muted)] flex justify-between items-center"
                    >
                      <div>
                        <div className="font-semibold text-[var(--text)] capitalize">{name}</div>
                        <div className="text-[10px] text-[var(--text-dim)]">
                          {comp.latency_ms !== undefined && `${comp.latency_ms} ms latency`}
                          {comp.build !== undefined && `Build: ${comp.build}`}
                          {comp.clients !== undefined && `WS clients: ${comp.clients}`}
                          {comp.dead_stream_len !== undefined && `Dead stream: ${comp.dead_stream_len}`}
                        </div>
                      </div>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                          comp.ok ? 'bg-emerald-950 text-emerald-300' : 'bg-red-950 text-red-300'
                        }`}
                      >
                        {comp.ok ? 'HEALTHY' : 'UNHEALTHY'}
                      </span>
                    </div>
                  ))}
              </div>

              <h4 className="font-bold text-[var(--text-dim)] uppercase tracking-wider text-[10px] pt-2">
                CCTV Cameras & Stream State
              </h4>
              <div className="space-y-1.5">
                {data?.cameras.map((c) => (
                  <div
                    key={c.camera_id}
                    className="p-2 rounded bg-[var(--bg-panel-2)] border border-[var(--border-muted)] flex justify-between items-center"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-2 w-2 rounded-full ${
                          c.state === 'ONLINE'
                            ? 'bg-emerald-400'
                            : c.state === 'STALLED' || c.state === 'RECONNECTING'
                            ? 'bg-amber-400 animate-pulse'
                            : 'bg-zinc-500'
                        }`}
                      />
                      <span className="font-mono font-bold text-[var(--text)]">{c.camera_id}</span>
                      {c.fps !== undefined && (
                        <span className="text-[10px] text-[var(--text-dim)] font-mono">
                          {c.fps.toFixed(1)} FPS
                        </span>
                      )}
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                        c.state === 'ONLINE'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-600/30'
                          : c.state === 'STALLED'
                          ? 'bg-amber-950 text-amber-300 border border-amber-600/30'
                          : c.state === 'RECONNECTING'
                          ? 'bg-amber-950 text-amber-300 border border-amber-600/30'
                          : 'bg-zinc-900 text-zinc-400 border border-zinc-700/30'
                      }`}
                    >
                      {c.state}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
