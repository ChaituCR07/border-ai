import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { DeepLinkBanner } from '../DeepLinkBanner';
import { useAlertDeepLink } from '../useAlertDeepLink';
import { useUIStore } from '../../../state/uiStore';

// Test harness component to exercise useAlertDeepLink inside MemoryRouter
function DeepLinkConsumer({ onLoaded }: { onLoaded?: (a: any) => void }) {
  const { alertId, alert, loading, error, clearAlertParam } = useAlertDeepLink(onLoaded);
  return (
    <div>
      <span data-testid="alert-id">{alertId || 'none'}</span>
      <span data-testid="loading">{loading ? 'yes' : 'no'}</span>
      <span data-testid="error">{error || 'none'}</span>
      <span data-testid="status">{alert?.status || 'none'}</span>
      <button onClick={clearAlertParam} data-testid="clear-btn">
        Clear
      </button>
      <DeepLinkBanner
        alertId={alertId}
        alert={alert}
        loading={loading}
        error={error}
        onDismiss={clearAlertParam}
      />
    </div>
  );
}

describe('useAlertDeepLink & DeepLinkBanner', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useUIStore.setState({
      selectedCameraId: null,
      activeSnapshotDrawer: null,
    });
  });

  it('renders nothing when no alert parameter is present', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <DeepLinkConsumer />
      </MemoryRouter>
    );

    expect(screen.getByTestId('alert-id')).toHaveTextContent('none');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('fetches alert detail and selects camera when ?alert=<id> is present', async () => {
    const mockAlert = {
      alert_id: 'alt-12345678',
      event_id: 'evt-001',
      priority: 'CRITICAL',
      status: 'OPEN',
      created_at: '2026-11-02T12:00:00Z',
      acknowledged_at: null,
      acknowledged_by: null,
      persisted: true,
      event: {
        camera_id: 'CAM-03',
        event_type: 'RESTRICTED_ZONE_ENTRY',
        threat_score: 95,
        plate: 'KA01AB1234',
        timestamp: '2026-11-02T12:00:00Z',
        snapshot_url: '/api/snapshots/cam3.jpg',
        snapshot_available: true,
      },
      notifications: { total: 1, sent: 1, pending: 0, failed: 0, cancelled: 0 },
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: mockAlert }),
    } as any);

    const onLoaded = vi.fn();

    render(
      <MemoryRouter initialEntries={['/?alert=alt-12345678']}>
        <DeepLinkConsumer onLoaded={onLoaded} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('status')).toHaveTextContent('OPEN');
    });

    expect(onLoaded).toHaveBeenCalledWith(mockAlert);
    expect(useUIStore.getState().selectedCameraId).toBe('CAM-03');
    expect(screen.getByText(/Active Alert/i)).toBeInTheDocument();
  });

  it('displays not-found error banner when alert endpoint returns 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ error: { code: 'NOT_FOUND', message: 'Not found' } }),
    } as any);

    render(
      <MemoryRouter initialEntries={['/?alert=expired-alert-id']}>
        <DeepLinkConsumer />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Alert not found or retention period expired/i)).toBeInTheDocument();
    });
  });

  it('renders resolved status banner when alert is resolved', async () => {
    const resolvedAlert = {
      alert_id: 'alt-resolved-1',
      event_id: 'evt-002',
      priority: 'HIGH',
      status: 'RESOLVED',
      resolved_at: '2026-11-02T12:30:00Z',
      resolved_by: 'supervisor-1',
      resolution: 'FALSE_POSITIVE',
      created_at: '2026-11-02T12:00:00Z',
      persisted: true,
      event: {
        camera_id: 'CAM-01',
        event_type: 'SPEED_ANOMALY',
        threat_score: 75,
        plate: null,
        timestamp: '2026-11-02T12:00:00Z',
        snapshot_url: null,
        snapshot_available: false,
      },
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: resolvedAlert }),
    } as any);

    render(
      <MemoryRouter initialEntries={['/?alert=alt-resolved-1']}>
        <DeepLinkConsumer />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/resolved \(FALSE_POSITIVE\) by supervisor-1/i)).toBeInTheDocument();
    });
  });

  it('clears query parameter and dismisses banner on dismiss click', async () => {
    const user = userEvent.setup();
    const resolvedAlert = {
      alert_id: 'alt-dismiss-1',
      event_id: 'evt-003',
      priority: 'HIGH',
      status: 'RESOLVED',
      resolved_by: 'admin',
      resolution: 'VERIFIED_THREAT',
      created_at: '2026-11-02T12:00:00Z',
      persisted: true,
      event: { camera_id: 'CAM-01', event_type: 'TRIPWIRE', threat_score: 80, timestamp: '2026-11-02T12:00:00Z' },
    };

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: resolvedAlert }),
    } as any);

    render(
      <MemoryRouter initialEntries={['/?alert=alt-dismiss-1']}>
        <DeepLinkConsumer />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/resolved/i)).toBeInTheDocument();
    });

    const dismissBtn = screen.getByRole('button', { name: /dismiss deep link banner/i });
    await user.click(dismissBtn);

    await waitFor(() => {
      expect(screen.getByTestId('alert-id')).toHaveTextContent('none');
    });
  });
});
