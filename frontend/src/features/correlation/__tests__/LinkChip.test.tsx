import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LinkChip } from '../LinkChip.js';
import type { Link } from '../types.js';

describe('LinkChip component', () => {
  const sampleLink: Link = {
    from_camera: 'CAM-01',
    to_camera: 'CAM-02',
    gap_s: 360,
    class: 'PLAUSIBLE',
    confidence: 1.0,
    factors: [
      { name: 'plate', value: 1.0, detail: 'exact match' },
      { name: 'timing', value: 1.0, detail: 'within expected range' },
    ],
    expected: { min_s: 240, typical_s: 360, max_s: 600 },
    missed_cameras: [],
  };

  it('renders class label, percentage, and data-class attribute', () => {
    render(<LinkChip link={sampleLink} />);
    const chip = screen.getByRole('button');
    expect(chip).toHaveAttribute('data-class', 'PLAUSIBLE');
    expect(chip).toHaveTextContent('PLAUSIBLE');
    expect(chip).toHaveTextContent('100%');
  });

  it('toggles factor popover on click and closes on Escape', () => {
    render(<LinkChip link={sampleLink} />);
    const chip = screen.getByRole('button');

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.click(chip);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/CAM-01 → CAM-02/)).toBeInTheDocument();
    expect(screen.getByText(/exact match/)).toBeInTheDocument();

    // Close on Escape
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('displays missed cameras when present in link', () => {
    const linkWithMissed: Link = {
      ...sampleLink,
      from_camera: 'CAM-02',
      to_camera: 'CAM-04',
      gap_s: 178,
      missed_cameras: ['CAM-03'],
    };

    render(<LinkChip link={linkWithMissed} />);
    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByText(/Missed camera\(s\): CAM-03/)).toBeInTheDocument();
  });
});

