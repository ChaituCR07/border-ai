import { z } from 'zod';

const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().default(4000),
  HOST: z.string().default('0.0.0.0'),
  DATABASE_URL: z.string().min(1, 'DATABASE_URL is required'),
  TEST_DATABASE_URL: z.string().optional(),
  CORS_ORIGINS: z.string().default('http://localhost:5173'),
  SNAPSHOT_DIR: z.string().default('../outputs/runs'),
  MJPEG_BASE_URL: z.string().default('http://localhost:8001'),
  THRESHOLDS_FILE: z.string().default('../configs/threat_thresholds.json'),
});

export type RawConfig = z.infer<typeof EnvSchema>;
export type Config = RawConfig & { corsOrigins: string[] };

export function loadConfig(source: NodeJS.ProcessEnv = process.env): Config {
  const parsed = EnvSchema.parse(source);
  return {
    ...parsed,
    corsOrigins: parsed.CORS_ORIGINS.split(',').map(s => s.trim()).filter(Boolean),
  };
}
