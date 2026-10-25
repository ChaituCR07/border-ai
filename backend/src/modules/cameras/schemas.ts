import { z } from 'zod';

const STREAM_URL_REGEX = /^(rtsp|rtsps|http|https|file):\/\/.+/i;
const CREDENTIALS_IN_URL_REGEX = /:\/\/[^/@]+@/;

export const CameraIdSchema = z.string().regex(/^[A-Za-z0-9_-]{2,32}$/, 'camera_id must be 2-32 alphanumeric characters, dashes or underscores');

export const StreamUrlSchema = z.string().refine(
  (url) => !CREDENTIALS_IN_URL_REGEX.test(url),
  { message: 'CREDENTIALS_IN_URL: Plaintext credentials in stream_url are forbidden', params: { code: 'CREDENTIALS_IN_URL' } }
).refine(
  (url) => STREAM_URL_REGEX.test(url),
  { message: 'stream_url must start with rtsp://, rtsps://, http://, https://, or file://' }
);

export const CreateCameraSchema = z.object({
  camera_id: CameraIdSchema,
  name: z.string().min(1).max(200),
  location_label: z.string().max(200).optional().nullable(),
  stream_url: StreamUrlSchema.optional().nullable(),
  credentials_ref: z.string().max(100).optional().nullable(),
  enabled: z.boolean().default(true),
}).strict();

export const UpdateCameraSchema = z.object({
  name: z.string().min(1).max(200),
  location_label: z.string().max(200).optional().nullable(),
  stream_url: StreamUrlSchema.optional().nullable(),
  credentials_ref: z.string().max(100).optional().nullable(),
  enabled: z.boolean().default(true),
}).strict();

export const CameraQuerySchema = z.object({
  enabled: z.enum(['true', 'false']).transform(v => v === 'true').optional(),
  q: z.string().optional(),
}).strict();

export const CameraResourceSchema = z.object({
  camera_id: z.string(),
  name: z.string().nullable(),
  location_label: z.string().nullable(),
  stream_url: z.string().nullable(),
  has_credentials: z.boolean(),
  credentials_ref: z.string().nullable(),
  enabled: z.boolean(),
  live_view_url: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});
