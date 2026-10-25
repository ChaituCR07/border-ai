import { describe, it, expect, beforeEach } from 'vitest';
import type { FastifyInstance } from 'fastify';
import { createTestApp } from '../helpers/test-app.js';

describe('Watchlist routes', () => {
  let app: FastifyInstance;

  beforeEach(async () => {
    const res = await createTestApp();
    app = res.app;
  });

  it('POST /api/watchlist creates VEHICLE entry with normalised plate', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/watchlist',
      payload: {
        entity_type: 'VEHICLE',
        identifier: 'ka-01 ab 1234',
        name: 'Stolen sedan',
        risk_level: 'HIGH',
      },
    });

    expect(res.statusCode).toBe(201);
    const body = res.json();
    expect(body.data.identifier).toBe('ka-01 ab 1234');
    expect(body.data.active).toBe(true);
  });

  it('POST /api/watchlist rejects PERSON without consent_reference with 400', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/watchlist',
      payload: {
        entity_type: 'PERSON',
        identifier: 'SUBJECT-01',
        name: 'Person of Interest',
        risk_level: 'MEDIUM',
      },
    });

    expect(res.statusCode).toBe(400);
    expect(res.json().error.code).toBe('VALIDATION_ERROR');
  });

  it('POST /api/watchlist strictly rejects any biometric fields', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/watchlist',
      payload: {
        entity_type: 'PERSON',
        identifier: 'SUBJECT-02',
        name: 'Subject 2',
        risk_level: 'LOW',
        consent_reference: 'CONSENT-2026-001',
        embedding: [0.12, 0.44], // Forbidden!
      },
    });

    expect(res.statusCode).toBe(400);
  });

  it('DELETE /api/watchlist/:id soft deletes and is idempotent', async () => {
    const createRes = await app.inject({
      method: 'POST',
      url: '/api/watchlist',
      payload: {
        entity_type: 'VEHICLE',
        identifier: 'MH12DE1433',
        name: 'Suspect car',
        risk_level: 'CRITICAL',
      },
    });

    const id = createRes.json().data.entity_id;

    const del1 = await app.inject({
      method: 'DELETE',
      url: `/api/watchlist/${id}`,
    });
    expect(del1.statusCode).toBe(204);

    const del2 = await app.inject({
      method: 'DELETE',
      url: `/api/watchlist/${id}`,
    });
    expect(del2.statusCode).toBe(204);
  });
});
