import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AlertToastStack } from './AlertToastStack';
import type { Toast } from './toastQueue';

function makeToast(overrides: {
  id?: string;
  count?: number;
  priority?: 'CRITICAL' | 'HIGH';
  persisted?: boolean;
}): Toast {
  const priority = overrides.priority ?? 'CRITICAL';
  return {
    id: overrides.id ?? 'alert-1',
    alert: {
      alert_id: overrides.id ?? 'alert-1',
      event_id: 'evt-1',
      priority,
      status: 'OPEN',
      acknowledged_by: null,
      acknowledged_at: null,
      created_at: new Date().toISOString(),
      persisted: overrides.persisted ?? true,
      event: {
        camera_id: 'CAM-03',
        event_type: 'RESTRICTED_ZONE_ENTRY',
        threat_score: 92,
        plate: 'KA01AB1234',
        timestamp: new Date().toISOString(),
        snapshot_url: null,
        snapshot_available: false,
      },
    },
    count: overrides.count ?? 1,
    createdAt: Date.now(),
    expiresAt: null,
    groupKey: 'CAM-03|KA01AB1234',
  };
}

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('AlertToastStack Component (ADR 0021 UI)', () => {
  it('renders CRITICAL toast with assertive role="alert" and HIGH toast with role="status"', () => {
    const toasts: Toast[] = [
      makeToast({ id: 'c1', priority: 'CRITICAL', persisted: true }),
      makeToast({ id: 'h1', priority: 'HIGH', persisted: true }),
    ];

    renderWithClient(<AlertToastStack toasts={toasts} onDismiss={vi.fn()} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL ALERT')).toBeInTheDocument();
    expect(screen.getByText('HIGH ALERT')).toBeInTheDocument();
  });

  it('renders coalesced badge ×3 when count > 1', () => {
    const toasts: Toast[] = [
      makeToast({ id: 'c1', count: 3, priority: 'CRITICAL', persisted: true }),
    ];

    renderWithClient(<AlertToastStack toasts={toasts} onDismiss={vi.fn()} />);

    expect(screen.getByText('×3')).toBeInTheDocument();
  });

  it('disables ACKNOWLEDGE button with syncing indicator when alert is unpersisted (persisted:false)', () => {
    const toasts: Toast[] = [
      makeToast({ id: 'u1', priority: 'CRITICAL', persisted: false }),
    ];

    renderWithClient(<AlertToastStack toasts={toasts} onDismiss={vi.fn()} />);

    expect(screen.getByText(/syncing with db/i)).toBeInTheDocument();
    const ackBtn = screen.getByRole('button', { name: /acknowledge/i });
    expect(ackBtn).toBeDisabled();
  });

  it('calls onDismiss when close button ✕ is clicked', async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    const toasts: Toast[] = [
      makeToast({ id: 'c1', priority: 'CRITICAL', persisted: true }),
    ];

    renderWithClient(<AlertToastStack toasts={toasts} onDismiss={onDismiss} />);

    const closeBtn = screen.getByRole('button', { name: /dismiss alert c1/i });
    await user.click(closeBtn);

    expect(onDismiss).toHaveBeenCalledWith('c1');
  });

  it('calls onViewAlert when VIEW button is clicked', async () => {
    const user = userEvent.setup();
    const onViewAlert = vi.fn();
    const toast = makeToast({ id: 'c1', priority: 'CRITICAL', persisted: true });

    renderWithClient(<AlertToastStack toasts={[toast]} onDismiss={vi.fn()} onViewAlert={onViewAlert} />);

    const viewBtn = screen.getByRole('button', { name: /^view$/i });
    await user.click(viewBtn);

    expect(onViewAlert).toHaveBeenCalledWith(toast);
  });

  it('renders +N more alerts chip when hidden toasts exceed MAX_VISIBLE (3)', () => {
    const toasts: Toast[] = [
      makeToast({ id: '1' }),
      makeToast({ id: '2' }),
      makeToast({ id: '3' }),
      makeToast({ id: '4' }),
      makeToast({ id: '5' }),
    ];

    renderWithClient(<AlertToastStack toasts={toasts} onDismiss={vi.fn()} />);

    expect(screen.getByText('+2 more alerts')).toBeInTheDocument();
  });
});
