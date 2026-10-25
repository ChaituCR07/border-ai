import { describe, it, expect, beforeEach } from 'vitest';
import { InMemoryWatchlistRepo } from '../../src/modules/watchlist/repo.memory.js';

describe('WatchlistRepo contract', () => {
  let repo: InMemoryWatchlistRepo;

  beforeEach(() => {
    repo = new InMemoryWatchlistRepo();
  });

  it('creates entry and finds active by normalized identifier', async () => {
    const entry = await repo.create({
      entity_type: 'VEHICLE',
      identifier: 'ka 01 ab 1234',
      normalized_identifier: 'KA01AB1234',
      name: 'Suspect Sedan',
      risk_level: 'HIGH',
    });

    expect(entry.entity_id).toBeDefined();
    expect(entry.active).toBe(true);

    const found = await repo.findActiveByIdentifier('VEHICLE', 'KA01AB1234');
    expect(found?.entity_id).toBe(entry.entity_id);
  });

  it('soft-deletes entry and excludes it from active list', async () => {
    const entry = await repo.create({
      entity_type: 'VEHICLE',
      identifier: 'DL01AA0001',
      normalized_identifier: 'DL01AA0001',
      name: 'Stolen Van',
      risk_level: 'CRITICAL',
    });

    const deleted = await repo.softDelete(entry.entity_id);
    expect(deleted).toBe(true);

    const activeList = await repo.list({ includeDeleted: false });
    expect(activeList.some(i => i.entity_id === entry.entity_id)).toBe(false);

    const allList = await repo.list({ includeDeleted: true });
    expect(allList.some(i => i.entity_id === entry.entity_id)).toBe(true);
  });
});
