import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';

describe('Cameras routes', () => {
  let app: FastifyInstance;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
  });

  it('GET /api/cameras returns list with envelope', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/api/cameras',
    });

    expect(res.statusCode).toBe(200);
    const body = res.json();
    expect(Array.isArray(body.data)).toBe(true);
  });

  it('POST /api/cameras creates a new camera with Location header', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/cameras',
      payload: {
        camera_id: 'CAM-01',
        name: 'Checkpoint 1',
        stream_url: 'rtsp://10.0.0.10:554/stream1',
        credentials_ref: 'CAM_01_CREDS',
        enabled: true,
      },
    });

    expect(res.statusCode).toBe(201);
    expect(res.headers.location).toBe('/api/cameras/CAM-01');
    const body = res.json();
    expect(body.data.camera_id).toBe('CAM-01');
    expect(body.data.has_credentials).toBe(true);
    expect(body.data.live_view_url).toBe('http://localhost:8001/cam/CAM-01.mjpg');
  });

  it('POST /api/cameras rejects plaintext credentials in stream_url with 400', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/cameras',
      payload: {
        camera_id: 'CAM-LEAK',
        name: 'Leaky Cam',
        stream_url: 'rtsp://admin:secretPass123@10.0.0.10:554/stream1',
      },
    });

    expect(res.statusCode).toBe(400);
    const body = res.json();
    expect(body.error.code).toBe('VALIDATION_ERROR');
    expect(JSON.stringify(body)).not.toContain('secretPass123');
  });

  it('POST /api/cameras returns 409 on duplicate camera_id', async () => {
    await app.inject({
      method: 'POST',
      url: '/api/cameras',
      payload: { camera_id: 'CAM-DUP', name: 'Cam 1' },
    });

    const res = await app.inject({
      method: 'POST',
      url: '/api/cameras',
      payload: { camera_id: 'CAM-DUP', name: 'Cam 2' },
    });

    expect(res.statusCode).toBe(409);
    expect(res.json().error.code).toBe('CONFLICT');
  });

  it('GET /api/cameras/:id returns detail or 404', async () => {
    await app.inject({
      method: 'POST',
      url: '/api/cameras',
      payload: { camera_id: 'CAM-FOUND', name: 'Found Cam' },
    });

    const res = await app.inject({
      method: 'GET',
      url: '/api/cameras/CAM-FOUND',
    });
    expect(res.statusCode).toBe(200);
    expect(res.json().data.name).toBe('Found Cam');

    const res404 = await app.inject({
      method: 'GET',
      url: '/api/cameras/CAM-404',
    });
    expect(res404.statusCode).toBe(404);
  });
});
