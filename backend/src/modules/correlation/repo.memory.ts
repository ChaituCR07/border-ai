import fs from 'node:fs';
import path from 'node:path';
import { CameraLink, TopologyIndex } from './topology.js';
import { CameraTopologyNode, CorrelationRepo, TopologyData, SequenceSearchFilters } from './repo.js';
import { SequenceMatch, SequenceHop, verifySequenceHops } from './sequence.js';
import type { EventsRepo, EventRow } from '../events/repo.js';
import { plateKey } from '../../common/plate.js';
import { isoToMicros } from '../investigation/journey.js';
import { round3 } from './link.js';

export class MemoryCorrelationRepo implements CorrelationRepo {
  private cameras = new Map<string, CameraTopologyNode>();
  private links: CameraLink[] = [];
  private localEvents: EventRow[] = [];

  constructor(
    private readonly eventsRepo?: EventsRepo,
    initialData?: {
      cameras?: Record<string, { map_x: number; map_y: number; name?: string; location_label?: string }>;
      links?: CameraLink[];
    }
  ) {
    if (initialData?.cameras && initialData.links) {
      this.seedMemory(initialData.cameras, initialData.links);
    } else {
      this.loadFromConfigFile();
    }
  }

  seedEvents(events: EventRow[]): void {
    this.localEvents = [...events];
  }

  private loadFromConfigFile(): void {
    const candidates = [
      path.resolve(process.cwd(), 'configs/camera_topology.json'),
      path.resolve(process.cwd(), '../configs/camera_topology.json'),
    ];
    for (const p of candidates) {
      if (fs.existsSync(p)) {
        try {
          const content = JSON.parse(fs.readFileSync(p, 'utf-8'));
          const cameras: Record<string, { map_x: number; map_y: number; name?: string; location_label?: string }> = {};
          for (const [camId, coords] of Object.entries(content.cameras ?? {})) {
            const c = coords as any;
            cameras[camId] = {
              map_x: c.map_x,
              map_y: c.map_y,
              name: `Camera ${camId}`,
              location_label: `Gate ${camId}`,
            };
          }
          this.seedMemory(cameras, content.links ?? []);
          return;
        } catch {
          // ignore error and proceed
        }
      }
    }
  }

  private seedMemory(
    cameras: Record<string, { map_x: number; map_y: number; name?: string; location_label?: string }>,
    links: CameraLink[]
  ): void {
    this.cameras.clear();
    for (const [camId, data] of Object.entries(cameras)) {
      this.cameras.set(camId, {
        camera_id: camId,
        name: data.name ?? `Camera ${camId}`,
        location_label: data.location_label ?? `Checkpoint ${camId}`,
        map_x: Number(data.map_x),
        map_y: Number(data.map_y),
      });
    }
    this.links = [...links];
  }

  async getTopology(): Promise<TopologyData> {
    const topo = new TopologyIndex(this.links);
    return {
      version: topo.version,
      cameras: Array.from(this.cameras.values()).sort((a, b) => a.camera_id.localeCompare(b.camera_id)),
      links: [...this.links],
    };
  }

  async seedTopology(
    cameras: Record<string, { map_x: number; map_y: number; name?: string; location_label?: string }>,
    links: CameraLink[]
  ): Promise<void> {
    this.seedMemory(cameras, links);
  }

  async sequenceSearch(filters: SequenceSearchFilters): Promise<SequenceMatch[]> {
    let allEvents: EventRow[] = [];
    if (this.eventsRepo) {
      const res = await this.eventsRepo.query({
        from: filters.from,
        to: filters.to,
      });
      allEvents = res.events;
    } else {
      allEvents = [...this.localEvents];
    }

    const fromMicros = isoToMicros(filters.from);
    const toMicros = isoToMicros(filters.to);

    // Filter to events within time range and with plate
    const eventsWithPlate = allEvents.filter(e => {
      if (!e.plate) return false;
      const ts = isoToMicros(e.timestamp);
      return ts >= fromMicros && ts < toMicros;
    });

    // Group by plate_key
    const byKey = new Map<string, EventRow[]>();
    for (const e of eventsWithPlate) {
      const key = plateKey(e.plate!);
      if (!byKey.has(key)) byKey.set(key, []);
      byKey.get(key)!.push(e);
    }

    const matches: SequenceMatch[] = [];

    for (const [key, events] of byKey.entries()) {
      // Sort events by timestamp ASC
      events.sort((a, b) => {
        const d = isoToMicros(a.timestamp) - isoToMicros(b.timestamp);
        return d < 0n ? -1 : d > 0n ? 1 : 0;
      });

      // Find an ordered sequence of events matching filters.cameras
      const findHop = (stepIdx: number, afterMicros: bigint): SequenceHop[] | null => {
        if (stepIdx >= filters.cameras.length) return [];
        const targetCam = filters.cameras[stepIdx]!;

        for (const e of events) {
          if (e.camera_id !== targetCam) continue;
          const eMicros = isoToMicros(e.timestamp);
          if (stepIdx > 0) {
            const gapS = Number(eMicros - afterMicros) / 1_000_000;
            if (gapS <= 0 || gapS > filters.maxHopGapS) continue;
          }

          const rest = findHop(stepIdx + 1, eMicros);
          if (rest !== null) {
            return [{ camera_id: e.camera_id, timestamp: e.timestamp, event_id: e.event_id }, ...rest];
          }
        }
        return null;
      };

      const matchedHops = findHop(0, 0n);
      if (matchedHops && verifySequenceHops(matchedHops, filters.maxHopGapS)) {
        const variants = Array.from(new Set(events.map(e => e.plate!).filter(Boolean)));
        const totalDuration = round3(
          Number(isoToMicros(matchedHops.at(-1)!.timestamp) - isoToMicros(matchedHops[0]!.timestamp)) / 1_000_000
        );

        matches.push({
          plate_key: key,
          representative_plate: variants[0] ?? key,
          plate_variants: variants,
          hops: matchedHops,
          total_duration_s: totalDuration,
        });
      }
    }

    // Sort by first hop timestamp DESC
    matches.sort((a, b) => {
      const d = isoToMicros(b.hops[0]!.timestamp) - isoToMicros(a.hops[0]!.timestamp);
      return d < 0n ? -1 : d > 0n ? 1 : 0;
    });

    return matches.slice(0, filters.limit);
  }
}
