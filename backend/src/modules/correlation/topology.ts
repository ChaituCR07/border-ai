import { createHash } from 'node:crypto';

export interface CameraLink {
  a: string;
  b: string;
  min_s: number;
  typical_s: number;
  max_s: number;
  direction?: 'both' | 'a_to_b';
  overlap?: boolean;
}

export interface Route {
  cameras: string[]; // inclusive of endpoints
  min_s: number;
  typical_s: number;
  max_s: number;
  intermediates: string[];
}

export interface TopologyIndexOptions {
  maxHops?: number;
  maxRoutesPerPair?: number;
}

export class TopologyIndex {
  readonly version: string;
  private routes = new Map<string, Route[]>();
  private overlapPairs = new Set<string>();

  constructor(links: CameraLink[], opts: TopologyIndexOptions = {}) {
    const maxHops = opts.maxHops ?? 4;
    const maxRoutes = opts.maxRoutesPerPair ?? 20;

    const adj = new Map<string, { to: string; l: CameraLink }[]>();
    const add = (from: string, to: string, l: CameraLink) => {
      if (!adj.has(from)) adj.set(from, []);
      adj.get(from)!.push({ to, l });
    };

    for (const l of links) {
      add(l.a, l.b, l);
      if ((l.direction ?? 'both') === 'both') {
        add(l.b, l.a, l);
      }
      if (l.overlap) {
        this.overlapPairs.add(`${l.a}>${l.b}`);
        this.overlapPairs.add(`${l.b}>${l.a}`);
      }
    }

    for (const start of [...adj.keys()].sort()) {
      const dfs = (node: string, path: string[], min: number, typ: number, max: number) => {
        if (path.length - 1 >= maxHops) return;
        for (const { to, l } of adj.get(node) ?? []) {
          if (path.includes(to)) continue; // simple routes only (no cycles)
          const p = [...path, to];
          const m = min + l.min_s;
          const t = typ + l.typical_s;
          const x = max + l.max_s;
          const key = `${start}>${to}`;
          const arr = this.routes.get(key) ?? [];
          arr.push({ cameras: p, min_s: m, typical_s: t, max_s: x, intermediates: p.slice(1, -1) });
          this.routes.set(key, arr);
          dfs(to, p, m, t, x);
        }
      };
      dfs(start, [start], 0, 0, 0);
    }

    for (const [k, arr] of this.routes) {
      // Deterministic order + cap (guard against path explosion)
      arr.sort((r1, r2) => r1.typical_s - r2.typical_s || r1.cameras.join().localeCompare(r2.cameras.join()));
      this.routes.set(k, arr.slice(0, maxRoutes));
    }

    const canon = [...links].map(l => [l.a, l.b, l.min_s, l.typical_s, l.max_s, l.direction ?? 'both', !!l.overlap])
      .sort((x, y) => String(x).localeCompare(String(y)));
    this.version = createHash('sha1').update(JSON.stringify(canon)).digest('hex').slice(0, 10);
  }

  routesBetween(a: string, b: string): Route[] {
    return this.routes.get(`${a}>${b}`) ?? [];
  }

  hasOverlap(a: string, b: string): boolean {
    return this.overlapPairs.has(`${a}>${b}`);
  }

  lower(a: string, b: string): number | null {
    const r = this.routesBetween(a, b);
    return r.length ? Math.min(...r.map(x => x.min_s)) : null;
  }

  upper(a: string, b: string): number | null {
    const r = this.routesBetween(a, b);
    return r.length ? Math.max(...r.map(x => x.max_s)) : null;
  }
}

