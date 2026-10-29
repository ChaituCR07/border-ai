import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PlateMatchBadge } from '../PlateMatchBadge.js';

describe('PlateMatchBadge component', () => {
  it('renders nothing for exact, none, or null match', () => {
    const { container: c1 } = render(<PlateMatchBadge match="exact" />);
    expect(c1.firstChild).toBeNull();

    const { container: c2 } = render(<PlateMatchBadge match="none" />);
    expect(c2.firstChild).toBeNull();

    const { container: c3 } = render(<PlateMatchBadge match={null} />);
    expect(c3.firstChild).toBeNull();
  });

  it('renders Look-alike badge for lookalike match with explanatory tooltip', () => {
    render(<PlateMatchBadge match="lookalike" />);
    const badge = screen.getByTestId('plate-match-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Look-alike');
    expect(badge).toHaveAttribute('title', expect.stringContaining('confusable'));
  });

  it('renders Prefix badge for prefix match', () => {
    render(<PlateMatchBadge match="prefix" />);
    const badge = screen.getByTestId('plate-match-badge');
    expect(badge).toHaveTextContent('Prefix');
  });

  it('renders Partial badge for contains or partial match', () => {
    render(<PlateMatchBadge match="contains" />);
    const badge = screen.getByTestId('plate-match-badge');
    expect(badge).toHaveTextContent('Partial');
  });
});
