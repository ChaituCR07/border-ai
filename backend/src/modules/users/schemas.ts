import { z } from 'zod';

export const RoleEnum = z.enum(['ADMIN', 'OPERATOR', 'INVESTIGATOR', 'VIEWER']);
export const StatusEnum = z.enum(['ACTIVE', 'DISABLED']);

export const CreateUserSchema = z.object({
  username: z.string().min(3).max(64),
  email: z.string().email().optional(),
  displayName: z.string().max(128).optional(),
  role: RoleEnum,
  password: z.string().min(12).max(128).optional(),
});

export type CreateUserInput = z.infer<typeof CreateUserSchema>;

export const UpdateUserSchema = z.object({
  email: z.string().email().optional().nullable(),
  displayName: z.string().max(128).optional().nullable(),
  role: RoleEnum.optional(),
  status: StatusEnum.optional(),
});

export type UpdateUserInput = z.infer<typeof UpdateUserSchema>;
