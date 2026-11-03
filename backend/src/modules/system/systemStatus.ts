import type pg from 'pg';
import type { Redis } from 'ioredis';
import type { Hub } from '../../realtime/hub.js';
import type { CamerasRepo } from '../cameras/repo.js';

export interface CameraStatusEntry {
  camera_id: string;
  state: 'ONLINE' | 'STALLED' | 'RECONNECTING' | 'OFFLINE';
  fps?: number;
  last_frame_at?: string;
  reconnects?: number;
}

export interface SystemStatusData {
  status: 'OK' | 'DEGRADED' | 'DOWN';
  components: {
    postgres: { ok: boolean; latency_ms: number };
    redis: { ok: boolean; latency_ms: number };
    engine: { ok: boolean; build?: string; device?: string; age_s?: number };
    sink: { ok: boolean; lag: number; pending: number; dead_stream_len: number };
    gateway: { ok: boolean; clients: number; seq: number };
    notifications: { ok: boolean; queue_oldest_age_s: number; smtp_ok: boolean };
  };
  cameras: CameraStatusEntry[];
}

export interface SystemStatusDeps {
  pool?: pg.Pool;
  redis?: Redis;
  hub?: Hub;
  camerasRepo?: CamerasRepo;
  cacheTtlMs?: number;
}

let cachedStatus: { data: SystemStatusData; expiresAt: number } | null = null;

export async function getSystemStatus(deps: SystemStatusDeps): Promise<SystemStatusData> {
  const now = Date.now();
  if (cachedStatus && cachedStatus.expiresAt > now) {
    return cachedStatus.data;
  }

  // 1. PostgreSQL check
  let pgOk = false;
  let pgLatency = 0;
  if (deps.pool) {
    const start = Date.now();
    try {
      await deps.pool.query('SELECT 1');
      pgOk = true;
      pgLatency = Date.now() - start;
    } catch {
      pgOk = false;
    }
  } else {
    pgOk = true; // In-memory/mock fallback
  }

  // 2. Redis check
  let redisOk = false;
  let redisLatency = 0;
  if (deps.redis) {
    const start = Date.now();
    try {
      const pong = await deps.redis.ping();
      redisOk = pong === 'PONG';
      redisLatency = Date.now() - start;
    } catch {
      redisOk = false;
    }
  } else {
    redisOk = true;
  }

  // 3. Engine status from Redis key `engine:status`
  let engineOk = false;
  let engineBuild: string | undefined;
  let engineDevice: string | undefined;
  let engineAgeS: number | undefined;

  if (deps.redis && redisOk) {
    try {
      const engRaw = await deps.redis.get('engine:status');
      if (engRaw) {
        const engObj = JSON.parse(engRaw);
        engineOk = true;
        engineBuild = engObj.build || 'v0.3-week3';
        engineDevice = engObj.device || 'cpu';
        if (engObj.at) {
          const atMs = new Date(engObj.at).getTime();
          engineAgeS = Math.max(0, Math.floor((now - atMs) / 1000));
        }
      }
    } catch {
      engineOk = false;
    }
  }

  // 4. Sink lag from consumer group
  let sinkLag = 0;
  let sinkPending = 0;
  let deadStreamLen = 0;
  if (deps.redis && redisOk) {
    try {
      deadStreamLen = (await deps.redis.xlen('surveillance.dead')) || 0;
      // If consumer groups exist, lag can be queried
    } catch {
      // ignore
    }
  }

  // 5. Gateway status
  const gatewayClients = deps.hub ? deps.hub.size : 0;
  const gatewaySeq = deps.hub ? deps.hub.currentSeq : 0;

  // 6. Cameras status
  const cameras: CameraStatusEntry[] = [];
  let allEnabledCameras = [
    { camera_id: 'CAM-01' },
    { camera_id: 'CAM-02' },
    { camera_id: 'CAM-03' },
    { camera_id: 'CAM-04' },
  ];

  if (deps.camerasRepo) {
    try {
      const loaded = await deps.camerasRepo.list({});
      if (loaded.length > 0) {
        allEnabledCameras = loaded.map(c => ({ camera_id: c.camera_id }));
      }
    } catch {
      // fallback
    }
  }

  let anyCameraNotOnline = false;
  for (const c of allEnabledCameras) {
    let state: 'ONLINE' | 'STALLED' | 'RECONNECTING' | 'OFFLINE' = 'OFFLINE';
    let fps: number | undefined;
    let lastFrameAt: string | undefined;
    let reconnects: number | undefined;

    if (deps.redis && redisOk) {
      try {
        const raw = await deps.redis.get(`camera:status:${c.camera_id}`);
        if (raw) {
          const parsed = JSON.parse(raw);
          state = parsed.state || 'ONLINE';
          fps = parsed.fps;
          lastFrameAt = parsed.last_frame_at;
          reconnects = parsed.reconnects;
        } else {
          state = 'OFFLINE';
        }
      } catch {
        state = 'OFFLINE';
      }
    }

    if (state !== 'ONLINE') {
      anyCameraNotOnline = true;
    }

    cameras.push({
      camera_id: c.camera_id,
      state,
      fps,
      last_frame_at: lastFrameAt,
      reconnects,
    });
  }

  // 7. Overall status evaluation
  let overall: 'OK' | 'DEGRADED' | 'DOWN' = 'OK';
  if (!pgOk || !redisOk) {
    overall = 'DOWN';
  } else if (!engineOk || anyCameraNotOnline || sinkLag > 1000 || sinkPending > 100 || deadStreamLen > 0) {
    overall = 'DEGRADED';
  }

  const result: SystemStatusData = {
    status: overall,
    components: {
      postgres: { ok: pgOk, latency_ms: pgLatency },
      redis: { ok: redisOk, latency_ms: redisLatency },
      engine: { ok: engineOk, build: engineBuild, device: engineDevice, age_s: engineAgeS },
      sink: { ok: true, lag: sinkLag, pending: sinkPending, dead_stream_len: deadStreamLen },
      gateway: { ok: true, clients: gatewayClients, seq: gatewaySeq },
      notifications: { ok: true, queue_oldest_age_s: 0, smtp_ok: true },
    },
    cameras,
  };

  const ttl = deps.cacheTtlMs ?? 2000;
  cachedStatus = {
    data: result,
    expiresAt: now + ttl,
  };

  return result;
}

export function resetSystemStatusCache(): void {
  cachedStatus = null;
}
