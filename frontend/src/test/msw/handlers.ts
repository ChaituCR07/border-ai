import { http, HttpResponse } from 'msw';
import { makeCamera, makeAlert, makeEvent, makeThreatSummary } from '../fixtures';

export const mockCameras = [
  makeCamera({ camera_id: 'CAM-01', name: 'North Gate East' }),
  makeCamera({ camera_id: 'CAM-02', name: 'North Gate West', live_view_url: 'http://localhost:8001/cam/CAM-02.mjpg' }),
  makeCamera({ camera_id: 'CAM-03', name: 'Perimeter Sector 9', live_view_url: 'http://localhost:8001/cam/CAM-03.mjpg' }),
  makeCamera({ camera_id: 'CAM-04', name: 'East Culvert', enabled: false, live_view_url: 'http://localhost:8001/cam/CAM-04.mjpg' }),
];

export let mockAlerts = [
  makeAlert({
    alert_id: 'alert-crit-1',
    priority: 'CRITICAL',
    status: 'OPEN',
    event: { camera_id: 'CAM-01', event_type: 'RESTRICTED_ZONE_ENTRY', threat_score: 95, plate: 'KA01AB1234', snapshot_url: '/api/snapshots/CAM-01/snap1.jpg' },
  }),
  makeAlert({
    alert_id: 'alert-high-1',
    priority: 'HIGH',
    status: 'OPEN',
    event: { camera_id: 'CAM-02', event_type: 'ANPR_WATCHLIST_HIT', threat_score: 75, plate: 'MH12DE1433', snapshot_url: null },
  }),
  makeAlert({
    alert_id: 'alert-med-1',
    priority: 'MEDIUM',
    status: 'OPEN',
    event: { camera_id: 'CAM-03', event_type: 'LOITERING', threat_score: 55, plate: null, snapshot_url: null },
  }),
];

export const handlers = [
  http.get(/.*\/api\/health$/, () => {
    return HttpResponse.json({ status: 'ok', uptime: 123.45 });
  }),

  http.get(/.*\/api\/ready$/, () => {
    return HttpResponse.json({ status: 'ready', database: 'connected' });
  }),

  http.get(/.*\/api\/cameras$/, () => {
    return HttpResponse.json({ data: mockCameras });
  }),

  http.get(/.*\/api\/analytics\/cameras$/, () => {
    return HttpResponse.json({
      data: mockCameras.map((c) => ({
        camera_id: c.camera_id,
        events: 42,
        alerts_open: c.camera_id === 'CAM-01' ? 1 : 0,
        max_threat_score: 95,
        last_event_at: '2026-10-26T12:00:00.000000Z',
      })),
    });
  }),

  http.get(/.*\/api\/analytics\/threats.*/, () => {
    return HttpResponse.json({ data: makeThreatSummary() });
  }),

  http.get(/.*\/api\/alerts(\?.*)?$/, ({ request }) => {
    const url = new URL(request.url);
    const priority = url.searchParams.get('priority');
    const camera_id = url.searchParams.get('camera_id');
    const status = url.searchParams.get('status');

    let filtered = [...mockAlerts];
    if (status) filtered = filtered.filter((a) => a.status === status);
    if (priority) filtered = filtered.filter((a) => a.priority === priority);
    if (camera_id) filtered = filtered.filter((a) => a.event.camera_id === camera_id);

    return HttpResponse.json({
      data: filtered,
      meta: { limit: 50, next_cursor: null, has_more: false },
    });
  }),

  http.patch(/.*\/api\/alerts\/([^/]+)\/acknowledge$/, ({ params }) => {
    const id = params[0] as string;
    const found = mockAlerts.find((a) => a.alert_id === id);
    if (!found) {
      return new HttpResponse(null, { status: 404 });
    }
    found.status = 'ACKNOWLEDGED';
    found.acknowledged_by = 'test-operator';
    found.acknowledged_at = new Date().toISOString();
    return HttpResponse.json({ data: found });
  }),

  http.get(/.*\/api\/events(\?.*)?$/, () => {
    return HttpResponse.json({
      data: [
        makeEvent({ event_id: 'e1', camera_id: 'CAM-01', severity: 'CRITICAL', threat_score: 95 }),
        makeEvent({ event_id: 'e2', camera_id: 'CAM-02', severity: 'HIGH', threat_score: 75, event_type: 'ANPR_WATCHLIST_HIT' }),
        makeEvent({ event_id: 'e3', camera_id: 'CAM-01', severity: 'LOW', threat_score: 20, event_type: 'LINE_CROSSING' }),
      ],
      meta: { limit: 10, next_cursor: null, has_more: false },
    });
  }),
];
