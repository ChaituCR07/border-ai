import { User, CreateUserData, UpdateUserData } from './users.types.js';

export interface IUsersRepo {
  create(data: CreateUserData): Promise<User>;
  findById(userId: string): Promise<User | null>;
  findByUsername(username: string): Promise<User | null>;
  list(): Promise<User[]>;
  update(userId: string, data: UpdateUserData): Promise<User | null>;
  delete(userId: string): Promise<boolean>;
  countActiveAdmins(): Promise<number>;
}
