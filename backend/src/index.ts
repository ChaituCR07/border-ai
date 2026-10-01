import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import path from "path";
import { Pool } from "pg";
import Redis from "ioredis";

dotenv.config({ path: path.resolve(__dirname, "../../.env") });

const app = express();
app.use(cors());
app.use(express.json());

const pool = new Pool({
  host: process.env.POSTGRES_HOST,
  port: Number(process.env.POSTGRES_PORT),
  database: process.env.POSTGRES_DB,
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
});

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: Number(process.env.REDIS_PORT),
  lazyConnect: true,
  maxRetriesPerRequest: 1,
});

app.get("/health", async (_req, res) => {
  const status = { service: "backend", postgres: "down", redis: "down" };

  try {
    await pool.query("SELECT 1");
    status.postgres = "up";
  } catch {}

  try {
    if (redis.status === "wait") await redis.connect();
    await redis.ping();
    status.redis = "up";
  } catch {}

  const ok = status.postgres === "up" && status.redis === "up";
  res.status(ok ? 200 : 503).json(status);
});

const port = Number(process.env.BACKEND_PORT) || 4000;
app.listen(port, () => console.log(`Backend listening on ${port}`));
