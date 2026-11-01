import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AnomalyList } from '../AnomalyList.js';
import type { Anomaly } from '../types.js';

describe('AnomalyList component', () => {
  it('renders "Findings (0) ✓ No anomalies" when anomalies array is empty', () => {
    render(<AnomalyList anomalies={[]} />);
    expect(screen.getByText('Findings (0)')).toBeInTheDocument();
    expect(screen.getByText('✓ No anomalies')).toBeInTheDocument();
  });

  it('renders warnings prominently with copy button', () => {
    const anomalies: Anomaly[] = [
      {
        type: 'IMPOSSIBLE_TRAVEL',
        severity: 'warning',
        trip_id: 'trip-1',
        trajectory_ids: ['T1'],
        message: 'Impossible travel detected between CAM-01 and CAM-04',
        evidence: {},
      },
    ];

    render(<AnomalyList anomalies={anomalies} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Impossible travel detected/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy anomaly message/ })).toBeInTheDocument();
  });

  it('collapses hints under accordion and expands on click', () => {
    const anomalies: Anomaly[] = [
      {
        type: 'MISSED_CAMERA',
        severity: 'info',
        trip_id: 'trip-1',
        trajectory_ids: ['T1'],
        message: 'Missed expected camera CAM-03',
        evidence: {},
      },
    ];

    render(<AnomalyList anomalies={anomalies} />);
    const toggle = screen.getByRole('button', { name: /Hints \(1\)/ });
    expect(toggle).toBeInTheDocument();
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    expect(screen.queryByText(/Missed expected camera CAM-03/)).not.toBeInTheDocument();

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText(/Missed expected camera CAM-03/)).toBeInTheDocument();
  });
});
