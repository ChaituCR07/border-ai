import { FastifyInstance, FastifyPluginAsync } from 'fastify';
import { UsersService } from './service.js';
import { CreateUserSchema, UpdateUserSchema } from './schemas.js';
import { notFound, badRequest } from '../../common/errors.js';

export function userRoutes(service: UsersService): FastifyPluginAsync {
  return async (app: FastifyInstance) => {
    // List users
    app.get(
      '/users',
      {
        config: { permission: 'users:manage' },
        schema: {
          tags: ['Users'],
          summary: 'List user accounts (Admin only)',
        },
      },
      async () => {
        const users = await service.listUsers();
        return { data: users };
      }
    );

    // Get user
    app.get(
      '/users/:id',
      {
        config: { permission: 'users:manage' },
        schema: {
          tags: ['Users'],
          summary: 'Get single user detail (Admin only)',
        },
      },
      async (req) => {
        const { id } = req.params as { id: string };
        const user = await service.getUser(id);
        if (!user) throw notFound('User');
        return { data: user };
      }
    );

    // Create user
    app.post(
      '/users',
      {
        config: { permission: 'users:manage' },
        schema: {
          tags: ['Users'],
          summary: 'Create a new user account (Admin only)',
        },
      },
      async (req, reply) => {
        const parsed = CreateUserSchema.safeParse(req.body);
        if (!parsed.success) {
          throw badRequest(parsed.error.errors[0]?.message ?? 'Invalid payload');
        }

        const created = await service.createUser(parsed.data, req.actor?.id);
        return reply.status(201).send({ data: created });
      }
    );

    // Update user
    app.patch(
      '/users/:id',
      {
        config: { permission: 'users:manage' },
        schema: {
          tags: ['Users'],
          summary: 'Update role or status of a user (Admin only)',
        },
      },
      async (req) => {
        const { id } = req.params as { id: string };
        const parsed = UpdateUserSchema.safeParse(req.body);
        if (!parsed.success) {
          throw badRequest(parsed.error.errors[0]?.message ?? 'Invalid payload');
        }

        const updated = await service.updateUser(id, parsed.data, req.actor?.id);
        return { data: updated };
      }
    );

    // Reset password
    app.post(
      '/users/:id/reset-password',
      {
        config: { permission: 'users:manage' },
        schema: {
          tags: ['Users'],
          summary: 'Reset user password and issue one-time credential (Admin only)',
        },
      },
      async (req) => {
        const { id } = req.params as { id: string };
        const result = await service.resetPassword(id, req.actor?.id);
        return { data: result };
      }
    );

    // Disable user
    app.post(
      '/users/:id/disable',
      {
        config: { permission: 'users:manage' },
        schema: {
          tags: ['Users'],
          summary: 'Disable user account (Admin only)',
        },
      },
      async (req) => {
        const { id } = req.params as { id: string };
        await service.disableUser(id, req.actor?.id);
        return { success: true, message: 'User account disabled' };
      }
    );

    // Delete user
    app.delete(
      '/users/:id',
      {
        config: { permission: 'users:manage' },
        schema: {
          tags: ['Users'],
          summary: 'Delete user account (Admin only)',
        },
      },
      async (req, reply) => {
        const { id } = req.params as { id: string };
        await service.deleteUser(id, req.actor?.id);
        return reply.status(204).send();
      }
    );
  };
}
