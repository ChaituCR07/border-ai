import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResultsTable, type EventItem } from '../ResultsTable.js';

describe('ResultsTable component', () => {
  const events: EventItem[] = [
    {
      event_id: '11111111-1111-1111-1111-111111111111',
      camera_id: 'CAM-01',
      event_type: 'VEHICLE_DETECTED',
      track_id: '1',
      severity: 'HIGH',
      threat_score: 82,
      timestamp: '2026-10-25T10:00:00.000000Z',
      snapshot_url: '/api/snapshots/cam1.jpg',
      has_snapshot: true,
      snapshot_available: true,
      plate: 'KA01AB1234',
      plate_match: 'lookalike',
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
      person_id: 'PER-99',
    },
  ];

  it('renders table headers and events with plate badge', () => {
    render(<ResultsTable events={events} onSelectEvent={vi.fn()} />);

    expect(screen.getByText('Time')).toBeInTheDocument();
    expect(screen.getByText('Camera')).toBeInTheDocument();
    expect(screen.getByText('CAM-01')).toBeInTheDocument();
    expect(screen.getByText('KA01AB1234')).toBeInTheDocument();
    expect(screen.getByText('Look-alike')).toBeInTheDocument();
  });

  it('calls onSelectEvent when clicking an event row', async () => {
    const handleSelect = vi.fn();
    render(<ResultsTable events={events} onSelectEvent={handleSelect} />);

    const inspectBtn = screen.getAllByRole('button', { name: /inspect/i })[0]!;
    await userEvent.click(inspectBtn);

    expect(handleSelect).toHaveBeenCalledWith(events[0]);
  });

  it('renders Journey button for events with plates', async () => {
    const handleJourney = vi.fn();
    render(
      <ResultsTable
        events={events}
        onSelectEvent={vi.fn()}
        onInvestigateJourney={handleJourney}
      />
    );

    const journeyBtn = screen.getByRole('button', { name: /journey/i });
    expect(journeyBtn).toBeInTheDocument();
    await userEvent.click(journeyBtn);
    expect(handleJourney).toHaveBeenCalledWith('KA01AB1234');
  });

  it('renders empty state when no events match', () => {
    render(<ResultsTable events={[]} onSelectEvent={vi.fn()} />);
    expect(screen.getByText(/no events match your criteria/i)).toBeInTheDocument();
  });
});
