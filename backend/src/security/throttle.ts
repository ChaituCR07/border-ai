export interface ThrottleStatus {
  blocked: boolean;
  retryAfterSeconds: number;
}

export class AuthThrottle {
  private memoryStore = new Map<
    string,
    { failures: number; windowStart: number; blockedUntil?: number }
  >();

  private readonly maxFailures = 5;
  private readonly windowMs = 15 * 60 * 1000; // 15 minutes

  check(key: string): ThrottleStatus {
    const entry = this.memoryStore.get(key);
    if (!entry) {
      return { blocked: false, retryAfterSeconds: 0 };
    }

    const now = Date.now();

    // Check if currently blocked
    if (entry.blockedUntil && entry.blockedUntil > now) {
      const retryAfter = Math.ceil((entry.blockedUntil - now) / 1000);
      return { blocked: true, retryAfterSeconds: retryAfter };
    }

    // Check if window expired
    if (now - entry.windowStart > this.windowMs) {
      this.memoryStore.delete(key);
      return { blocked: false, retryAfterSeconds: 0 };
    }

    return { blocked: false, retryAfterSeconds: 0 };
  }

  recordFailure(key: string): ThrottleStatus {
    const now = Date.now();
    let entry = this.memoryStore.get(key);

    if (!entry || now - entry.windowStart > this.windowMs) {
      entry = { failures: 1, windowStart: now };
      this.memoryStore.set(key, entry);
      return { blocked: false, retryAfterSeconds: 0 };
    }

    entry.failures += 1;

    if (entry.failures >= this.maxFailures) {
      // Exponential backoff: 5s, 15s, 30s, 60s...
      const exponent = entry.failures - this.maxFailures;
      const delaySeconds = Math.min(300, 5 * Math.pow(2, exponent));
      entry.blockedUntil = now + delaySeconds * 1000;
      return { blocked: true, retryAfterSeconds: delaySeconds };
    }

    return { blocked: false, retryAfterSeconds: 0 };
  }

  reset(key: string): void {
    this.memoryStore.delete(key);
  }

  clear(): void {
    this.memoryStore.clear();
  }
}

export const authThrottle = new AuthThrottle();
