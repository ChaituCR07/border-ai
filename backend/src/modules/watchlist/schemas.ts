import { z } from 'zod';

export const WatchlistIdSchema = z.string().uuid('id must be a valid UUID');
export const RiskLevelEnum = z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);
export const EntityTypeEnum = z.enum(['VEHICLE', 'PERSON']);

// Reject any biometric field explicitly
const BiometricGuard = z.object({
  embedding: z.never({ message: 'Biometric embeddings are not accepted via the REST API' }).optional(),
  image: z.never({ message: 'Biometric images are not accepted via the REST API' }).optional(),
  face: z.never({ message: 'Biometric face data is not accepted via the REST API' }).optional(),
  photo: z.never({ message: 'Biometric photos are not accepted via the REST API' }).optional(),
});

export const CreateWatchlistSchema = BiometricGuard.and(
  z.object({
    entity_type: EntityTypeEnum,
    identifier: z.string().min(1).max(64),
    name: z.string().min(1).max(200),
    risk_level: RiskLevelEnum,
    notes: z.string().max(2000).optional().nullable(),
    consent_reference: z.string().max(100).optional().nullable(),
  }).strict()
).superRefine((data, ctx) => {
  if (data.entity_type === 'PERSON' && !data.consent_reference?.trim()) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'CONSENT_REQUIRED: PERSON entity requires a valid consent_reference under ADR 0009',
      path: ['consent_reference'],
    });
  }
});

export const WatchlistQuerySchema = z.object({
  entity_type: EntityTypeEnum.optional(),
  risk_level: RiskLevelEnum.optional(),
  q: z.string().optional(),
  include_deleted: z.enum(['true', 'false']).transform(v => v === 'true').optional(),
}).strict();

export const WatchlistResourceSchema = z.object({
  entity_id: z.string().uuid(),
  entity_type: EntityTypeEnum,
  identifier: z.string(),
  name: z.string(),
  risk_level: RiskLevelEnum,
  notes: z.string().nullable(),
  consent_reference: z.string().nullable(),
  active: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});
