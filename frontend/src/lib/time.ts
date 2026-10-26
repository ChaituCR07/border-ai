export type TzMode = 'UTC' | 'LOCAL';

export function formatTime(iso: string, mode: TzMode = 'UTC'): string {
  if (!iso) return '–';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '–';
    return d.toLocaleTimeString('en-GB', {
      hour12: false,
      timeZone: mode === 'UTC' ? 'UTC' : undefined,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }) + (mode === 'UTC' ? ' UTC' : '');
  } catch {
    return '–';
  }
}

export function formatDateFull(iso: string, mode: TzMode = 'UTC'): string {
  if (!iso) return '–';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '–';
    return d.toLocaleString('en-GB', {
      hour12: false,
      timeZone: mode === 'UTC' ? 'UTC' : undefined,
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }) + (mode === 'UTC' ? ' UTC' : '');
  } catch {
    return '–';
  }
}

export function relativeTime(iso: string, now: number = Date.now()): string {
  if (!iso) return '–';
  try {
    const ms = new Date(iso).getTime();
    if (isNaN(ms)) return '–';
    const s = Math.max(0, Math.round((now - ms) / 1000));
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
  } catch {
    return '–';
  }
}
