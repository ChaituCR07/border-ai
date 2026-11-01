import { CameraLink } from './topology.js';

export interface CameraTopologyNode {
  camera_id: string;
  name: string;
  location_label: string;
  map_x: number;
  map_y: number;
}

export interface TopologyData {
  version: string;
  cameras: CameraTopologyNode[];
  links: CameraLink[];
}

export interface CorrelationRepo {
  getTopology(): Promise<TopologyData>;
  seedTopology(
    cameras: Record<string, { map_x: number; map_y: number; name?: string; location_label?: string }>,
    links: CameraLink[]
  ): Promise<void>;
}
