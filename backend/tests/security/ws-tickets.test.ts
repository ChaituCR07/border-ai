import { describe, it, expect, beforeEach } from 'vitest';
import { ticketStore } from '../../src/modules/realtime/tickets.js';

describe('WebSocket Single-Use Tickets', () => {
  beforeEach(() => {
    ticketStore.clear();
  });

  it('issues a ticket with 30s expiration', () => {
    const { ticket, expiresIn } = ticketStore.createTicket('user-1', 'OPERATOR', 'ses-1');
    expect(ticket).toBeDefined();
    expect(ticket.length).toBeGreaterThanOrEqual(16);
    expect(expiresIn).toBe(30);
  });

  it('consumes a ticket on first use and deletes it immediately', () => {
    const { ticket } = ticketStore.createTicket('user-2', 'ADMIN', 'ses-2');

    // First use -> valid
    const consumedFirst = ticketStore.consumeTicket(ticket);
    expect(consumedFirst).not.toBeNull();
    expect(consumedFirst?.userId).toBe('user-2');
    expect(consumedFirst?.role).toBe('ADMIN');
    expect(consumedFirst?.sid).toBe('ses-2');

    // Second use -> deleted / null
    const consumedSecond = ticketStore.consumeTicket(ticket);
    expect(consumedSecond).toBeNull();
  });

  it('rejects nonexistent or expired ticket', () => {
    const bogus = ticketStore.consumeTicket('completely-invalid-ticket-value');
    expect(bogus).toBeNull();
  });

  it('enforces rate limit of 10 tickets per minute per user', () => {
    const userId = 'user-spam';
    for (let i = 0; i < 10; i++) {
      ticketStore.createTicket(userId, 'VIEWER', `ses-${i}`);
    }

    // 11th request throws
    expect(() => {
      ticketStore.createTicket(userId, 'VIEWER', 'ses-11');
    }).toThrowError(/Maximum 10 WebSocket tickets per minute/i);
  });
});
