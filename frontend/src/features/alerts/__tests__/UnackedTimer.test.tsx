import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UnackedTimer, formatElapsed } from '../UnackedTimer';

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('UnackedTimer Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('formatElapsed helper', () => {
    it('formats seconds correctly', () => {
      expect(formatElapsed(45)).toBe('45s');
      expect(formatElapsed(0)).toBe('0s');
    });

    it('formats minutes and seconds correctly', () => {
      expect(formatElapsed(60)).toBe('1m 0s');
      expect(formatElapsed(125)).toBe('2m 5s');
    });

    it('formats hours and minutes correctly', () => {
      expect(formatElapsed(3600)).toBe('1h 0m');
      expect(formatElapsed(3665)).toBe('1h 1m');
    });
  });

  it('renders null when status is not OPEN (e.g. ACKNOWLEDGED or RESOLVED)', () => {
    const { container } = renderWithQuery(
      <UnackedTimer
        createdAt={new Date(Date.now() - 50_000).toISOString()}
        status="ACKNOWLEDGED"
      />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders normal timer prefix when age is below warning threshold', () => {
    // 30 seconds ago, critical threshold 300s -> < 150s is normal
    const createdAt = new Date(Date.now() - 30_000).toISOString();
    renderWithQuery(
      <UnackedTimer
        createdAt={createdAt}
        status="OPEN"
        criticalAfterSeconds={300}
      />
    );

    const timer = screen.getByRole('timer');
    expect(timer).toBeInTheDocument();
    expect(timer).toHaveTextContent('⏱');
    expect(timer).toHaveTextContent('30s');
  });

  it('renders approaching warning badge when age exceeds half the critical threshold', () => {
    // 200 seconds ago, critical threshold 300s -> 150s-300s is approaching
    const createdAt = new Date(Date.now() - 200_000).toISOString();
    renderWithQuery(
      <UnackedTimer
        createdAt={createdAt}
        status="OPEN"
        criticalAfterSeconds={300}
      />
    );

    const timer = screen.getByRole('timer');
    expect(timer).toBeInTheDocument();
    expect(timer).toHaveTextContent('⚠️ Approaching');
    expect(timer).toHaveTextContent('3m 20s');
  });

  it('renders pulsing escalated badge when age exceeds critical threshold', () => {
    // 350 seconds ago, critical threshold 300s -> escalated
    const createdAt = new Date(Date.now() - 350_000).toISOString();
    renderWithQuery(
      <UnackedTimer
        createdAt={createdAt}
        status="OPEN"
        criticalAfterSeconds={300}
      />
    );

    const timer = screen.getByRole('timer');
    expect(timer).toBeInTheDocument();
    expect(timer).toHaveTextContent('🚨 Escalated');
    expect(timer).toHaveTextContent('5m 50s');
  });
});
