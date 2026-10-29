import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FilterPanel } from '../FilterPanel.js';

describe('FilterPanel component', () => {
  const facets = {
    total: 350,
    by_camera: [
      { value: 'CAM-01', count: 200 },
      { value: 'CAM-02', count: 150 },
    ],
    by_event_type: [
      { value: 'VEHICLE_DETECTED', count: 250 },
      { value: 'RESTRICTED_ZONE_ENTRY', count: 100 },
    ],
    by_severity: {
      CRITICAL: 50,
      HIGH: 100,
      MEDIUM: 120,
      LOW: 80,
    },
  };

  it('renders total count, time presets, and facet lists', () => {
    render(
      <FilterPanel
        state={{}}
        facets={facets}
        onPatchState={vi.fn()}
        onReset={vi.fn()}
      />
    );

    expect(screen.getByText('(350 matching)')).toBeInTheDocument();
    expect(screen.getByText('Last 1h')).toBeInTheDocument();
    expect(screen.getByText('Last 24h')).toBeInTheDocument();
    expect(screen.getByText('Last 7d')).toBeInTheDocument();
    expect(screen.getByText('CAM-01')).toBeInTheDocument();
    expect(screen.getByText('VEHICLE_DETECTED')).toBeInTheDocument();
  });

  it('triggers onPatchState when clicking a time preset', async () => {
    const handlePatch = vi.fn();
    render(
      <FilterPanel
        state={{}}
        facets={facets}
        onPatchState={handlePatch}
        onReset={vi.fn()}
      />
    );

    const btn1h = screen.getByRole('button', { name: 'Last 1h' });
    await userEvent.click(btn1h);

    expect(handlePatch).toHaveBeenCalledTimes(1);
    const patch = handlePatch.mock.calls[0]?.[0];
    expect(patch.from).toBeDefined();
    expect(patch.to).toBeDefined();
  });

  it('shows Person Identifier input only for INVESTIGATOR or ADMIN', () => {
    const { rerender } = render(
      <FilterPanel
        state={{}}
        facets={facets}
        userRole="OPERATOR"
        onPatchState={vi.fn()}
        onReset={vi.fn()}
      />
    );
    expect(screen.queryByPlaceholderText('e.g. PER-1002')).not.toBeInTheDocument();

    rerender(
      <FilterPanel
        state={{}}
        facets={facets}
        userRole="INVESTIGATOR"
        onPatchState={vi.fn()}
        onReset={vi.fn()}
      />
    );
    expect(screen.getByPlaceholderText('e.g. PER-1002')).toBeInTheDocument();
  });
});
