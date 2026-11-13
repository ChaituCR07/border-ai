import { z } from 'zod';

export const LoginSchema = z.object({
  username: z.string().min(1, 'Username is required').max(128),
  password: z.string().min(1, 'Password is required').max(128),
});

export type LoginInput = z.infer<typeof LoginSchema>;

export const ChangePasswordSchema = z.object({
  currentPassword: z.string().min(1, 'Current password is required').max(128),
  newPassword: z.string().min(12, 'New password must be at least 12 characters').max(128),
});

export type ChangePasswordInput = z.infer<typeof ChangePasswordSchema>;

export const AuthResponseSchema = z.object({
  accessToken: z.string(),
  expiresIn: z.number(),
  user: z.object({
    userId: z.string(),
    username: z.string(),
    displayName: z.string().nullable().optional(),
    role: z.enum(['ADMIN', 'OPERATOR', 'INVESTIGATOR', 'VIEWER']),
    mustChangePassword: z.boolean(),
  }),
});
