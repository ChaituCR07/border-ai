import type { FastifyError, FastifyReply, FastifyRequest } from 'fastify';
import { hasZodFastifySchemaValidationErrors } from 'fastify-type-provider-zod';

export class AppError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = 'AppError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export const notFound = (what: string) => new AppError(404, 'NOT_FOUND', `${what} not found`);
export const conflict = (message: string) => new AppError(409, 'CONFLICT', message);
export const validationError = (message: string, details?: unknown) =>
  new AppError(400, 'VALIDATION_ERROR', message, details);

export function errorHandler(
  err: FastifyError | AppError | Error,
  req: FastifyRequest,
  reply: FastifyReply,
) {
  const requestId = req.id || 'unknown';

  if (hasZodFastifySchemaValidationErrors(err)) {
    return reply.status(400).send({
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Request validation failed',
        details: err.validation?.map(v => ({
          path: (v as any).instancePath ?? (v as any).params?.missingProperty ?? 'body',
          issue: v.message,
        })) ?? [],
        request_id: requestId,
      },
    });
  }

  if (err instanceof AppError) {
    return reply.status(err.status).send({
      error: {
        code: err.code,
        message: err.message,
        details: err.details,
        request_id: requestId,
      },
    });
  }

  // Fastify internal errors (e.g. 404, 429)
  const statusCode = (err as any).statusCode || 500;
  if (statusCode === 404) {
    return reply.status(404).send({
      error: {
        code: 'NOT_FOUND',
        message: err.message || 'Route not found',
        request_id: requestId,
      },
    });
  }
  if (statusCode === 429) {
    return reply.status(429).send({
      error: {
        code: 'RATE_LIMITED',
        message: 'Too many requests, please slow down',
        request_id: requestId,
      },
    });
  }

  req.log.error({ err, requestId }, 'Unhandled application error');

  return reply.status(500).send({
    error: {
      code: 'INTERNAL',
      message: 'Internal server error',
      request_id: requestId,
    },
  });
}
