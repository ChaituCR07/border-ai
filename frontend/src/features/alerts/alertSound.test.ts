import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  unlockAudio,
  playAlertSound,
  isAudioUnlocked,
  isAudioMuted,
  setAudioMuted,
  _resetAudioForTesting,
} from './alertSound';

class FakeGain {
  gain = {
    setValueAtTime: vi.fn(),
    exponentialRampToValueAtTime: vi.fn(),
  };
  connect = vi.fn().mockImplementation((dest) => dest);
}

class FakeOscillator {
  frequency = { value: 0 };
  type = 'sine';
  connect = vi.fn().mockImplementation((dest) => dest);
  start = vi.fn();
  stop = vi.fn();
}

class FakeAudioContext {
  state: AudioContextState = 'suspended';
  currentTime = 0;
  destination = {};

  async resume() {
    this.state = 'running';
  }

  createGain() {
    return new FakeGain();
  }

  createOscillator() {
    return new FakeOscillator();
  }
}

describe('Web Audio Alert Sound Synthesizer (ADR 0021)', () => {
  beforeEach(() => {
    _resetAudioForTesting();
  });

  it('does not play sound before audio context is unlocked by user gesture', () => {
    expect(isAudioUnlocked()).toBe(false);
    expect(playAlertSound('CRITICAL')).toBe(false);
  });

  it('unlocks audio context and plays tone sequence', async () => {
    const unlocked = await unlockAudio(FakeAudioContext as unknown as typeof AudioContext);
    expect(unlocked).toBe(true);
    expect(isAudioUnlocked()).toBe(true);

    const played = playAlertSound('CRITICAL', 1000);
    expect(played).toBe(true);
  });

  it('enforces 3-second rate limit between alert chimes', async () => {
    await unlockAudio(FakeAudioContext as unknown as typeof AudioContext);

    // First sound plays at t = 1000
    expect(playAlertSound('CRITICAL', 1000)).toBe(true);

    // Burst sound at t = 2000 (< 3s later) is rate-limited
    expect(playAlertSound('CRITICAL', 2000)).toBe(false);

    // Sound at t = 4500 (> 3s later) plays successfully
    expect(playAlertSound('HIGH', 4500)).toBe(true);
  });

  it('does not play when user has muted alert sounds', async () => {
    await unlockAudio(FakeAudioContext as unknown as typeof AudioContext);

    setAudioMuted(true);
    expect(isAudioMuted()).toBe(true);
    expect(playAlertSound('CRITICAL', 1000)).toBe(false);

    setAudioMuted(false);
    expect(isAudioMuted()).toBe(false);
    expect(playAlertSound('CRITICAL', 1000)).toBe(true);
  });
});
