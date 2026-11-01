import fs from 'node:fs';
import path from 'node:path';
import { z } from 'zod';

export const CameraTopologyConfigSchema = z.object({
  version: z.number().int().min(1),
  cameras: z.record(
    z.string(),
    z.object({
      map_x: z.number().min(0).max(100),
      map_y: z.number().min(0).max(100),
    })
  ),
  links: z.array(
    z.object({
      a: z.string(),
      b: z.string(),
      min_s: z.number().int().nonnegative(),
      typical_s: z.number().int().nonnegative(),
      max_s: z.number().int().nonnegative(),
      direction: z.enum(['both', 'a_to_b']).default('both'),
      overlap: z.boolean().default(false),
      notes: z.string().optional(),
    })
  ),
});

export type CameraTopologyConfig = z.infer<typeof CameraTopologyConfigSchema>;

export interface TopologyValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export function validateTopologyConfig(config: CameraTopologyConfig): TopologyValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  const cameraIds = new Set(Object.keys(config.cameras));
  const connectedCameras = new Set<string>();
  const seenPairs = new Set<string>();

  // Check camera coordinates
  for (const [camId, coords] of Object.entries(config.cameras)) {
    if (coords.map_x < 0 || coords.map_x > 100 || coords.map_y < 0 || coords.map_y > 100) {
      errors.push(`Camera '${camId}' coordinates (${coords.map_x}, ${coords.map_y}) must be between 0 and 100.`);
    }
  }

  // Validate each link
  for (const link of config.links) {
    // 1. Unknown camera check
    if (!cameraIds.has(link.a)) {
      errors.push(`Link references unknown camera a: '${link.a}'.`);
    }
    if (!cameraIds.has(link.b)) {
      errors.push(`Link references unknown camera b: '${link.b}'.`);
    }

    // 2. Self-link check
    if (link.a === link.b) {
      errors.push(`Self-link forbidden on camera '${link.a}'.`);
    }

    // 3. Min <= Typical <= Max
    if (!(link.min_s <= link.typical_s && link.typical_s <= link.max_s)) {
      errors.push(
        `Link between '${link.a}' and '${link.b}' violates min_s (${link.min_s}) <= typical_s (${link.typical_s}) <= max_s (${link.max_s}).`
      );
    }

    // 4. Duplicate or contradictory links
    const pair1 = `${link.a}>${link.b}`;
    const pair2 = `${link.b}>${link.a}`;
    const undirectedKey = [link.a, link.b].sort().join('<->');

    if (seenPairs.has(undirectedKey)) {
      errors.push(`Duplicate or contradictory link defined between '${link.a}' and '${link.b}'.`);
    }
    seenPairs.add(undirectedKey);

    // 5. Zero min_s warning on non-overlap links
    if (link.min_s === 0 && !link.overlap) {
      warnings.push(`Link between '${link.a}' and '${link.b}' has min_s = 0 but overlap is false.`);
    }

    connectedCameras.add(link.a);
    connectedCameras.add(link.b);
  }

  // 6. Camera with no links warning
  for (const camId of cameraIds) {
    if (!connectedCameras.has(camId)) {
      warnings.push(`Camera '${camId}' has no links defined in the topology.`);
    }
  }

  // 7. Route explosion check (max 20 routes per pair within 4 hops)
  const adj = new Map<string, string[]>();
  for (const link of config.links) {
    if (!adj.has(link.a)) adj.set(link.a, []);
    adj.get(link.a)!.push(link.b);
    if ((link.direction ?? 'both') === 'both') {
      if (!adj.has(link.b)) adj.set(link.b, []);
      adj.get(link.b)!.push(link.a);
    }
  }

  const routeCounts = new Map<string, number>();
  for (const start of cameraIds) {
    const dfs = (curr: string, visited: Set<string>, hops: number) => {
      if (hops >= 4) return;
      for (const next of adj.get(curr) ?? []) {
        if (visited.has(next)) continue;
        const key = `${start}>${next}`;
        const cnt = (routeCounts.get(key) ?? 0) + 1;
        routeCounts.set(key, cnt);
        visited.add(next);
        dfs(next, visited, hops + 1);
        visited.delete(next);
      }
    };
    dfs(start, new Set([start]), 0);
  }

  for (const [pair, count] of routeCounts.entries()) {
    if (count > 20) {
      errors.push(
        `Route explosion detected between '${pair}': ${count} simple routes found within 4 hops (maximum allowed is 20). Simplify graph.`
      );
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

export function runTopologyCheck(filePath?: string): boolean {
  let targetPath = filePath || path.resolve(process.cwd(), 'configs/camera_topology.json');
  if (!fs.existsSync(targetPath)) {
    const parentPath = path.resolve(process.cwd(), '../configs/camera_topology.json');
    if (fs.existsSync(parentPath)) {
      targetPath = parentPath;
    }
  }
  console.log(`[topology:check] Checking topology config from ${targetPath}...`);

  if (!fs.existsSync(targetPath)) {
    console.error(`Error: File not found at ${targetPath}`);
    return false;
  }

  const raw = fs.readFileSync(targetPath, 'utf-8');
  let parsedJson: unknown;
  try {
    parsedJson = JSON.parse(raw);
  } catch (err: any) {
    console.error(`Error: Invalid JSON syntax in ${targetPath}: ${err.message}`);
    return false;
  }

  const parsedConfig = CameraTopologyConfigSchema.safeParse(parsedJson);
  if (!parsedConfig.success) {
    console.error(`Error: Schema validation failed:\n`, parsedConfig.error.format());
    return false;
  }

  const result = validateTopologyConfig(parsedConfig.data);

  for (const warn of result.warnings) {
    console.warn(`[topology:check] WARN: ${warn}`);
  }

  if (!result.valid) {
    for (const err of result.errors) {
      console.error(`[topology:check] ERROR: ${err}`);
    }
    console.error(`[topology:check] FAILED with ${result.errors.length} error(s).`);
    return false;
  }

  console.log(`[topology:check] PASSED! Validated ${Object.keys(parsedConfig.data.cameras).length} cameras and ${parsedConfig.data.links.length} links.`);
  return true;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const ok = runTopologyCheck();
  process.exit(ok ? 0 : 1);
}
