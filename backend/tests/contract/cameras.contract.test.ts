import { describe, it, expect, beforeEach } from 'vitest';
import { InMemoryCamerasRepo } from '../../src/modules/cameras/repo.memory.js';

describe('CamerasRepo contract', () => {
  let repo: InMemoryCamerasRepo;

  beforeEach(() => {
    repo = new InMemoryCamerasRepo('http://localhost:8001');
  });

  it('creates and retrieves camera by ID', async () => {
    const cam = await repo.create({
      camera_id: 'CAM-01',
      name: 'North Gate East',
      location_label: 'Sector 4',
      stream_url: 'rtsp://10.0.4.23:554/live',
      credentials_ref: 'CAM_CREDS_01',
      enabled: true,
    });

    expect(cam.camera_id).toBe('CAM-01');
    expect(cam.has_credentials).toBe(true);
    expect(cam.live_view_url).toBe('http://localhost:8001/cam/CAM-01.mjpg');

    const found = await repo.getById('CAM-01');
    expect(found).toEqual(cam);
  });

  it('returns null for unknown camera ID', async () => {
    const found = await repo.getById('UNKNOWN');
    expect(found).toBeNull();
  });

  it('updates camera mutable properties', async () => {
    await repo.create({ camera_id: 'CAM-02', name: 'South Gate' });
    const updated = await repo.update('CAM-02', {
      name: 'South Gate Main',
      location_label: 'Sector 9',
      enabled: false,
    });

    expect(updated?.name).toBe('South Gate Main');
    expect(updated?.location_label).toBe('Sector 9');
    expect(updated?.enabled).toBe(false);
  });
});
