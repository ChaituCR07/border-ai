import crypto from 'node:crypto';
import { Role } from '../../security/jwt.js';

export interface WebSocketTicket {
  ticket: string;
  userId: string;
  role: Role;
  sid: string;
  createdAt: number;
}

export class TicketStore {
  private tickets = new Map<string, WebSocketTicket>();
  private readonly ttlMs = 30_000; // 30 seconds validity
  private userRateLimiter = new Map<string, number[]>(); // userId -> timestamps

  createTicket(userId: string, role: Role, sid: string): { ticket: string; expiresIn: number } {
    // Rate limit: max 10 tickets/min/user
    const now = Date.now();
    const timestamps = (this.userRateLimiter.get(userId) || []).filter((t) => t > now - 60_000);
    if (timestamps.length >= 10) {
      throw new Error('RATE_LIMIT_EXCEEDED: Maximum 10 WebSocket tickets per minute');
    }
    timestamps.push(now);
    this.userRateLimiter.set(userId, timestamps);

    const ticket = crypto.randomBytes(16).toString('base64url');
    this.tickets.set(ticket, {
      ticket,
      userId,
      role,
      sid,
      createdAt: now,
    });

    return { ticket, expiresIn: 30 };
  }

  /**
   * Consume ticket atomically: deletes on first use and returns the ticket payload
   */
  consumeTicket(ticketStr: string): WebSocketTicket | null {
    const found = this.tickets.get(ticketStr);
    if (!found) return null;

    // Single-use: delete immediately
    this.tickets.delete(ticketStr);

    const now = Date.now();
    if (now - found.createdAt > this.ttlMs) {
      return null; // Expired
    }

    return found;
  }

  clear() {
    this.tickets.clear();
    this.userRateLimiter.clear();
  }
}

export const ticketStore = new TicketStore();
