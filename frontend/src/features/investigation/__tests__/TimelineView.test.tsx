import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TimelineView } from '../TimelineView.js';
import type { EventItem } from '../ResultsTable.js';

describe('TimelineView component', () => {
  const events: EventItem[] = [
    {
      event_id: '11111111-1111-1111-1111-111111111111',
      camera_id: 'CAM-01',
      event_type: 'VEHICLE_DETECTED',
      track_id: '1',
      severity: 'HIGH',
      threat_score: 82,
      timestamp: '2026-10-25T10:00:00.000000Z',
      snapshot_url: null,
      has_snapshot: false,
      snapshot_available: false,
    },
    {
      event_id: '22222222-2222-2222-2222-222222222222',
      camera_id: 'CAM-02',
      event_type: 'PERSON_DETECTED',
      track_id: '2',
      severity: 'LOW',
      threat_score: 15,
      timestamp: '2026-10-25T10:05:00.000000Z',
      snapshot_url: null,
      has_snapshot: false,
      snapshot_available: false,
    },
  ];

  it('renders camera lane labels and lane statistics', () => {
    render(<TimelineView events={events} onSelectEvent={vi.fn()} />);

    expect(screen.getByText('Camera Timeline Lanes')).toBeInTheDocument();
    expect(screen.getByText(/showing 2 events across 2 cameras/i)).toBeInTheDocument();
    expect(screen.getByText('CAM-01')).toBeInTheDocument();
    expect(screen.getByText('CAM-02')).toBeInTheDocument();
  });

  it('renders empty message when events list is empty', () => {
    render(<TimelineView events={[]} onSelectEvent={vi.fn()} />);
    expect(screen.getByText(/no timeline data available/i)).toBeInTheDocument();
  });
});
