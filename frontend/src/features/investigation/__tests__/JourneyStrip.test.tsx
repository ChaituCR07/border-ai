import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { JourneyStrip } from '../JourneyStrip.js';

describe('JourneyStrip component', () => {
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
                total_events: 4,
                span_s: 110,
                plate_variants: ['KA01AB1234', 'KA0IAB1234'],
                sightings: [
                  {
                    camera_id: 'CAM-03',
                    first_seen: '2026-10-25T10:00:00.000000Z',
                    last_seen: '2026-10-25T10:00:10.000000Z',
                    event_count: 2,
                    max_score: 75,
                    plates: ['KA01AB1234'],
                    event_types: ['VEHICLE_DETECTED'],
                    event_ids: ['e1', 'e2'],
                  },
                  {
                    camera_id: 'CAM-04',
                    first_seen: '2026-10-25T10:00:38.000000Z',
                    last_seen: '2026-10-25T10:00:38.000000Z',
                    event_count: 1,
                    max_score: 60,
                    plates: ['KA0IAB1234'],
                    event_types: ['VEHICLE_DETECTED'],
                    event_ids: ['e3'],
                  },
                ],
                transitions: [
                  {
                    from: 'CAM-03',
                    to: 'CAM-04',
                    gap_s: 28,
                  },
                ],
              },
              meta: {
                truncated: false,
                total_matching: 4,
              },
            }),
        })
      )
    );
  });

  it('renders sightings, gap times, and OCR variants banner', async () => {
    render(<JourneyStrip plate="KA01AB1234" onClose={vi.fn()} />);

    expect(screen.getByRole('region', { name: /vehicle journey sequence/i })).toBeInTheDocument();

    expect(await screen.findByText('CAM-03')).toBeInTheDocument();
    expect(await screen.findByText('CAM-04')).toBeInTheDocument();
    expect(await screen.findByText('+28s')).toBeInTheDocument();
    const variants = await screen.findAllByText('KA0IAB1234');
    expect(variants.length).toBeGreaterThanOrEqual(1);
  });

  it('calls onSelectSighting when clicking a sighting card', async () => {
    const handleSelect = vi.fn();
    render(
      <JourneyStrip
        plate="KA01AB1234"
        onClose={vi.fn()}
        onSelectSighting={handleSelect}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('CAM-03')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText('CAM-03'));
    expect(handleSelect).toHaveBeenCalledWith(
      'CAM-03',
      '2026-10-25T10:00:00.000000Z',
      '2026-10-25T10:00:10.000000Z'
    );
  });
});
