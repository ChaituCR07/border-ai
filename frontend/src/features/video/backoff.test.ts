import { describe, it, expect } from 'vitest';
import { backoffMs } from './backoff';

describe('backoffMs', () => {
  it('grows exponentially and respects maximum cap', () => {
    const noJitter = () => 1; // rand()=1 -> maximum value
    expect(backoffMs(0, 1000, 15000, noJitter)).toBe(1000);
    expect(backoffMs(1, 1000, 15000, noJitter)).toBe(2000);
    expect(backoffMs(2, 1000, 15000, noJitter)).toBe(4000);
    expect(backoffMs(3, 1000, 15000, noJitter)).toBe(8000);
    expect(backoffMs(4, 1000, 15000, noJitter)).toBe(15000); // capped at 15000
    expect(backoffMs(10, 1000, 15000, noJitter)).toBe(15000); // capped at 15000
  });

  it('never returns less than half the exponential base value', () => {
    const minJitter = () => 0; // rand()=0 -> base/2
    expect(backoffMs(0, 1000, 15000, minJitter)).toBe(500);
    expect(backoffMs(3, 1000, 15000, minJitter)).toBe(4000);
    expect(backoffMs(4, 1000, 15000, minJitter)).toBe(7500);
  });
});
