// Web Audio oscillator synthesizer for alert notifications (ADR 0021)
let ctx: AudioContext | null = null;
let lastPlayed = 0;
let muted = false;

// Check localStorage for user mute preference
if (typeof window !== 'undefined' && window.localStorage) {
  try {
    muted = window.localStorage.getItem('borderai_alert_muted') === 'true';
  } catch {
    // Ignore storage errors in sandboxed environments
  }
}

export function isAudioUnlocked(): boolean {
  return ctx !== null && ctx.state === 'running';
}

export function isAudioMuted(): boolean {
  return muted;
}

export function setAudioMuted(val: boolean): void {
  muted = val;
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem('borderai_alert_muted', String(val));
    } catch {
      // Ignore
    }
  }
}

/**
 * MUST be called in response to a direct user gesture (e.g. click).
 */
export async function unlockAudio(AudioContextClass: typeof AudioContext = (typeof window !== 'undefined' ? window.AudioContext : undefined as unknown as typeof AudioContext)): Promise<boolean> {
  try {
    if (!ctx) {
      ctx = new AudioContextClass();
    }
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }
    return ctx.state === 'running';
  } catch {
    return false;
  }
}

/**
 * Plays an alert audio chime using Web Audio oscillators.
 * Returns true if sound was scheduled, false if blocked, muted, or rate-limited.
 */
export function playAlertSound(
  priority: 'CRITICAL' | 'HIGH',
  now = Date.now()
): boolean {
  if (muted) return false;
  if (!ctx || ctx.state !== 'running') return false;
  // Rate limit: at most one sound per 3 seconds (ADR 0021)
  if (lastPlayed > 0 && now - lastPlayed < 3_000) return false;
  lastPlayed = now;

  try {
    const tones = priority === 'CRITICAL' ? [880, 660, 880] : [660];
    tones.forEach((f, i) => {
      const o = ctx!.createOscillator();
      const g = ctx!.createGain();
      o.frequency.value = f;
      o.type = 'sine';
      const startTime = ctx!.currentTime + i * 0.2;
      g.gain.setValueAtTime(0.0001, startTime);
      g.gain.exponentialRampToValueAtTime(0.25, startTime + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.18);
      o.connect(g);
      g.connect(ctx!.destination);
      o.start(startTime);
      o.stop(startTime + 0.2);
    });
    return true;
  } catch {
    return false;
  }
}

export function _resetAudioForTesting() {
  ctx = null;
  lastPlayed = 0;
  muted = false;
}
