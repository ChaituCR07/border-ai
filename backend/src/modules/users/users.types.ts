import { Role } from '../../security/jwt.js';

export type UserStatus = 'ACTIVE' | 'DISABLED';

export interface User {
  userId: string;
  username: string;
  email?: string | null;
  displayName?: string | null;
  role: Role;
  passwordHash: string;
  passwordHistory: string[];
  status: UserStatus;
  mustChangePassword: boolean;
  tokenVersion: number;
  failedAttempts: number;
  lastFailedAt?: Date | null;
  lastLoginAt?: Date | null;
  createdAt: Date;
  createdBy?: string | null;
  updatedAt: Date;
}

export interface CreateUserData {
  username: string;
  email?: string | null;
  displayName?: string | null;
  role: Role;
  passwordHash: string;
  mustChangePassword?: boolean;
  createdBy?: string | null;
}

export interface UpdateUserData {
  email?: string | null;
  displayName?: string | null;
  role?: Role;
  status?: UserStatus;
  mustChangePassword?: boolean;
  passwordHash?: string;
  passwordHistory?: string[];
  tokenVersion?: number;
  failedAttempts?: number;
  lastFailedAt?: Date | null;
  lastLoginAt?: Date | null;
}
