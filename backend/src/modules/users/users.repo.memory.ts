import crypto from 'node:crypto';
import { IUsersRepo } from './users.repo.js';
import { User, CreateUserData, UpdateUserData } from './users.types.js';

export class MemoryUsersRepo implements IUsersRepo {
  private users = new Map<string, User>(); // userId -> User
  private usernameIndex = new Map<string, string>(); // lower(username) -> userId

  async create(data: CreateUserData): Promise<User> {
    const lower = data.username.toLowerCase();
    if (this.usernameIndex.has(lower)) {
      throw new Error(`Username '${data.username}' already exists`);
    }

    const now = new Date();
    const user: User = {
      userId: crypto.randomUUID(),
      username: data.username,
      email: data.email ?? null,
      displayName: data.displayName ?? null,
      role: data.role,
      passwordHash: data.passwordHash,
      passwordHistory: [data.passwordHash],
      status: 'ACTIVE',
      mustChangePassword: data.mustChangePassword ?? false,
      tokenVersion: 1,
      failedAttempts: 0,
      lastFailedAt: null,
      lastLoginAt: null,
      createdAt: now,
      createdBy: data.createdBy ?? null,
      updatedAt: now,
    };

    this.users.set(user.userId, user);
    this.usernameIndex.set(lower, user.userId);
    return { ...user };
  }

  async findById(userId: string): Promise<User | null> {
    const u = this.users.get(userId);
    return u ? { ...u } : null;
  }

  async findByUsername(username: string): Promise<User | null> {
    const id = this.usernameIndex.get(username.toLowerCase());
    if (!id) return null;
    const u = this.users.get(id);
    return u ? { ...u } : null;
  }

  async list(): Promise<User[]> {
    return Array.from(this.users.values()).map((u) => ({ ...u }));
  }

  async update(userId: string, data: UpdateUserData): Promise<User | null> {
    const existing = this.users.get(userId);
    if (!existing) return null;

    const updated: User = {
      ...existing,
      ...data,
      updatedAt: new Date(),
    };

    this.users.set(userId, updated);
    return { ...updated };
  }

  async delete(userId: string): Promise<boolean> {
    const existing = this.users.get(userId);
    if (!existing) return false;
    this.usernameIndex.delete(existing.username.toLowerCase());
    return this.users.delete(userId);
  }

  async countActiveAdmins(): Promise<number> {
    let count = 0;
    for (const u of this.users.values()) {
      if (u.role === 'ADMIN' && u.status === 'ACTIVE') {
        count++;
      }
    }
    return count;
  }

  clear() {
    this.users.clear();
    this.usernameIndex.clear();
  }
}
