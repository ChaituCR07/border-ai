import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EventDrawer } from '../EventDrawer.js';

describe('EventDrawer component', () => {
  const targetId = '11111111-1111-1111-1111-111111111111';

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              data: {
                event: {
                  event_id: targetId,
                  camera_id: 'CAM-01',
                  event_type: 'RESTRICTED_ZONE_ENTRY',
                  threat_score: 92,
                  severity: 'CRITICAL',
                  timestamp: '2026-10-25T10:00:00.000000Z',
                  plate: 'KA01AB1234',
                  snapshot_available: false,
                  explanation: {
                    factors: [
                      { name: 'restricted_zone', points: 40 },
                      { name: 'nighttime', points: 25 },
                    ],
                  },
                },
                same_camera_around: [
                  {
                    event_id: '22222222-2222-2222-2222-222222222222',
                    camera_id: 'CAM-01',
                    event_type: 'VEHICLE_DETECTED',
                    threat_score: 50,
                    severity: 'MEDIUM',
                    timestamp: '2026-10-25T10:00:20.000000Z',
                  },
                ],
                same_subject_elsewhere: [
                  {
                    event_id: '33333333-3333-3333-3333-333333333333',
                    camera_id: 'CAM-02',
                    event_type: 'ANPR_MATCH',
                    threat_score: 70,
                    severity: 'HIGH',
                    timestamp: '2026-10-25T10:05:00.000000Z',
                  },
                ],
                alert: null,
              },
            }),
        })
      )
    );
  });

  it('renders nothing when eventId is null', () => {
    const { container } = render(<EventDrawer eventId={null} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('fetches context and displays event details, explanation factors and context lists', async () => {
    render(<EventDrawer eventId={targetId} onClose={vi.fn()} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('92 / 100')).toBeInTheDocument();
      expect(screen.getByText('CRITICAL')).toBeInTheDocument();
      expect(screen.getByText('Snapshot no longer available')).toBeInTheDocument();
      expect(screen.getByText(/restricted zone/i)).toBeInTheDocument();
      expect(screen.getByText('+40 pts')).toBeInTheDocument();
      expect(screen.getByText(/Same Camera \(CAM-01\) ±60s/)).toBeInTheDocument();
      expect(screen.getByText(/Same Subject Elsewhere ±15m/)).toBeInTheDocument();
    });
  });

  it('calls onClose when clicking close button or pressing Escape', async () => {
    const handleClose = vi.fn();
    render(<EventDrawer eventId={targetId} onClose={handleClose} />);

    const closeBtn = screen.getByRole('button', { name: /close drawer/i });
    await userEvent.click(closeBtn);
    expect(handleClose).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(2);
  });

  it('triggers action deep links for camera, plate, and journey', async () => {
    const handleFilterCamera = vi.fn();
    const handleFilterPlate = vi.fn();
    const handleViewJourney = vi.fn();

    render(
      <EventDrawer
        eventId={targetId}
        onClose={vi.fn()}
        onFilterCamera={handleFilterCamera}
        onFilterPlate={handleFilterPlate}
        onViewJourney={handleViewJourney}
      />
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /filter this camera/i })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /filter this camera/i }));
    expect(handleFilterCamera).toHaveBeenCalledWith('CAM-01');

    await userEvent.click(screen.getByRole('button', { name: /filter this plate/i }));
    expect(handleFilterPlate).toHaveBeenCalledWith('KA01AB1234');

    await userEvent.click(screen.getByRole('button', { name: /view vehicle journey/i }));
    expect(handleViewJourney).toHaveBeenCalledWith('KA01AB1234');
  });
});
