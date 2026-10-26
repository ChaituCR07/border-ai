export function backoffMs(
  attempt: number,
  base: number = 1000,
  cap: number = 15000,
  rand: () => number = Math.random
): number {
  const exp = Math.min(cap, base * 2 ** attempt);
  // Equal jitter: range is [exp / 2, exp]
  return Math.round(exp / 2 + rand() * (exp / 2));
}
