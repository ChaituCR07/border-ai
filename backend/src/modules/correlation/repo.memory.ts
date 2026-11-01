import fs from 'node:fs';
import path from 'node:path';
import { CameraLink, TopologyIndex } from './topology.js';
import { CameraTopologyNode, CorrelationRepo, TopologyData } from './repo.js';

export class MemoryCorrelationRepo implements CorrelationRepo {
  private cameras = new Map<string, CameraTopologyNode>();
  private links: CameraLink[] = [];

  constructor(initialData?: {
    cameras?: Record<string, { map_x: number; map_y: number; name?: string; location_label?: string }>;
    links?: CameraLink[];
  }) {
    if (initialData?.cameras && initialData.links) {
      this.seedMemory(initialData.cameras, initialData.links);
    } else {
      this.loadFromConfigFile();
    }
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
}
