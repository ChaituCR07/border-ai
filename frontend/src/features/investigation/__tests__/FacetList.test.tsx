import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FacetList } from '../FacetList.js';

describe('FacetList component', () => {
  const items = [
    { value: 'CAM-01', count: 120 },
    { value: 'CAM-02', count: 85 },
    { value: 'CAM-03', count: 42 },
  ];

  it('renders title and facet items with counts', () => {
    render(<FacetList title="Cameras" items={items} selected={[]} onChange={vi.fn()} />);

    expect(screen.getByText('Cameras')).toBeInTheDocument();
    expect(screen.getByText('CAM-01')).toBeInTheDocument();
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('CAM-02')).toBeInTheDocument();
    expect(screen.getByText('85')).toBeInTheDocument();
  });

  it('toggles selection on click', async () => {
    const handleChange = vi.fn();
    render(<FacetList title="Cameras" items={items} selected={['CAM-01']} onChange={handleChange} />);

    // Click on CAM-02 to add
    const cam2 = screen.getByText('CAM-02');
    await userEvent.click(cam2);
    expect(handleChange).toHaveBeenCalledWith(['CAM-01', 'CAM-02']);
  });
});
