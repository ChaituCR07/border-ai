import { describe, it, expect } from 'vitest';
import { TopologyIndex, CameraLink } from '../../src/modules/correlation/topology.js';

describe('TopologyIndex', () => {
  const sampleLinks: CameraLink[] = [
    { a: 'CAM-01', b: 'CAM-02', min_s: 240, typical_s: 360, max_s: 600, direction: 'both', overlap: false },
    { a: 'CAM-02', b: 'CAM-03', min_s: 90, typical_s: 150, max_s: 300, direction: 'both', overlap: false },
    { a: 'CAM-03', b: 'CAM-04', min_s: 15, typical_s: 30, max_s: 90, direction: 'both', overlap: false },
    { a: 'CAM-02', b: 'CAM-04', min_s: 300, typical_s: 420, max_s: 720, direction: 'both', overlap: false },
    { a: 'CAM-04', b: 'CAM-05', min_s: 40, typical_s: 70, max_s: 180, direction: 'both', overlap: false },
  ];

  it('computes routes in both directions for bidirectional links', () => {
    const topo = new TopologyIndex(sampleLinks);
    const routesFwd = topo.routesBetween('CAM-01', 'CAM-02');
    const routesRev = topo.routesBetween('CAM-02', 'CAM-01');

    expect(routesFwd).toHaveLength(1);
    expect(routesRev).toHaveLength(1);
    expect(routesFwd[0].min_s).toBe(240);
    expect(routesRev[0].min_s).toBe(240);
  });

  it('respects directed links (a_to_b)', () => {
    const links: CameraLink[] = [
      { a: 'CAM-A', b: 'CAM-B', min_s: 10, typical_s: 20, max_s: 30, direction: 'a_to_b' },
    ];
    const topo = new TopologyIndex(links);
    expect(topo.routesBetween('CAM-A', 'CAM-B')).toHaveLength(1);
    expect(topo.routesBetween('CAM-B', 'CAM-A')).toHaveLength(0);
  });

  it('enumerates multiple routes and tracks intermediates', () => {
    const topo = new TopologyIndex(sampleLinks);
    // CAM-02 to CAM-04 can go direct or via CAM-03
    const routes = topo.routesBetween('CAM-02', 'CAM-04');
    expect(routes.length).toBe(2);

    const direct = routes.find(r => r.intermediates.length === 0);
    const via03 = routes.find(r => r.intermediates.length === 1 && r.intermediates[0] === 'CAM-03');

    expect(direct).toBeDefined();
    expect(direct?.typical_s).toBe(420);

    expect(via03).toBeDefined();
    expect(via03?.typical_s).toBe(150 + 30); // 180
    expect(via03?.min_s).toBe(90 + 15); // 105
  });

  it('enforces maxHops limit', () => {
    // 5-camera chain: 1-2-3-4-5 requires 4 hops. With maxHops: 3, 1->5 should not exist.
    const chainLinks: CameraLink[] = [
      { a: 'CAM-01', b: 'CAM-02', min_s: 10, typical_s: 20, max_s: 30 },
      { a: 'CAM-02', b: 'CAM-03', min_s: 10, typical_s: 20, max_s: 30 },
      { a: 'CAM-03', b: 'CAM-04', min_s: 10, typical_s: 20, max_s: 30 },
      { a: 'CAM-04', b: 'CAM-05', min_s: 10, typical_s: 20, max_s: 30 },
    ];
    const topoLimited = new TopologyIndex(chainLinks, { maxHops: 3 });
    expect(topoLimited.routesBetween('CAM-01', 'CAM-05')).toHaveLength(0);
    expect(topoLimited.routesBetween('CAM-01', 'CAM-04')).toHaveLength(1);

    const topoFull = new TopologyIndex(chainLinks, { maxHops: 4 });
    expect(topoFull.routesBetween('CAM-01', 'CAM-05')).toHaveLength(1);
  });

  it('prevents cycles and does not revisit any camera', () => {
    const triangleLinks: CameraLink[] = [
      { a: 'A', b: 'B', min_s: 10, typical_s: 20, max_s: 30 },
      { a: 'B', b: 'C', min_s: 10, typical_s: 20, max_s: 30 },
      { a: 'C', b: 'A', min_s: 10, typical_s: 20, max_s: 30 },
    ];
    const topo = new TopologyIndex(triangleLinks, { maxHops: 4 });
    const routes = topo.routesBetween('A', 'C');
    for (const route of routes) {
      const unique = new Set(route.cameras);
      expect(unique.size).toBe(route.cameras.length);
    }
  });

  it('calculates lower and upper bounds correctly', () => {
    const topo = new TopologyIndex(sampleLinks);
    // CAM-02 -> CAM-04: direct is 300-720, via CAM-03 is (90+15=105) to (300+90=390)
    // lower = min(300, 105) = 105; upper = max(720, 390) = 720
    expect(topo.lower('CAM-02', 'CAM-04')).toBe(105);
    expect(topo.upper('CAM-02', 'CAM-04')).toBe(720);
    expect(topo.lower('CAM-01', 'CAM-99')).toBeNull();
  });

  it('correctly tracks overlap links', () => {
    const overlapLinks: CameraLink[] = [
      { a: 'A', b: 'B', min_s: 0, typical_s: 5, max_s: 10, overlap: true },
      { a: 'B', b: 'C', min_s: 10, typical_s: 20, max_s: 30, overlap: false },
    ];
    const topo = new TopologyIndex(overlapLinks);
    expect(topo.hasOverlap('A', 'B')).toBe(true);
    expect(topo.hasOverlap('B', 'A')).toBe(true);
    expect(topo.hasOverlap('B', 'C')).toBe(false);
  });

  it('produces stable canonical version hash regardless of link input order', () => {
    const topo1 = new TopologyIndex(sampleLinks);
    const topo2 = new TopologyIndex([...sampleLinks].reverse());
    expect(topo1.version).toBe(topo2.version);
    expect(topo1.version.length).toBe(10);

    const modifiedLinks: CameraLink[] = [
      ...sampleLinks.slice(1),
      { ...sampleLinks[0], typical_s: sampleLinks[0].typical_s + 1 },
    ];
    const topo3 = new TopologyIndex(modifiedLinks);
    expect(topo3.version).not.toBe(topo1.version);
  });

  it('enforces maxRoutesPerPair cap on dense graphs', () => {
    // Generate a dense complete graph of 5 nodes
    const nodes = ['N1', 'N2', 'N3', 'N4', 'N5'];
    const denseLinks: CameraLink[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        denseLinks.push({ a: nodes[i], b: nodes[j], min_s: 10, typical_s: 20, max_s: 30 });
      }
    }
    const cap = 5;
    const topo = new TopologyIndex(denseLinks, { maxRoutesPerPair: cap, maxHops: 4 });
    const routes = topo.routesBetween('N1', 'N5');
    expect(routes.length).toBeLessThanOrEqual(cap);
  });
});
