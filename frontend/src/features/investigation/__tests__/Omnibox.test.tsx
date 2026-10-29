import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Omnibox } from '../Omnibox.js';

describe('Omnibox component', () => {
  it('renders input with placeholder and search button', () => {
    render(<Omnibox onSearch={vi.fn()} />);
    expect(screen.getByRole('combobox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^search$/i })).toBeInTheDocument();
  });

  it('submits parsed query on button click', async () => {
    const handleSearch = vi.fn();
    render(<Omnibox onSearch={handleSearch} />);

    const input = screen.getByRole('combobox');
    await userEvent.type(input, 'cam:CAM-01 sev:CRITICAL');

    const searchBtn = screen.getByRole('button', { name: /^search$/i });
    await userEvent.click(searchBtn);

    expect(handleSearch).toHaveBeenCalledTimes(1);
    const parsed = handleSearch.mock.calls[0]?.[0];
    expect(parsed.state.camera_id).toEqual(['CAM-01']);
    expect(parsed.state.severity).toEqual(['CRITICAL']);
  });

  it('focuses input when global / key is pressed outside inputs', () => {
    render(<Omnibox onSearch={vi.fn()} />);
    const input = screen.getByRole('combobox');
    expect(input).not.toHaveFocus();

    fireEvent.keyDown(window, { key: '/' });
    expect(input).toHaveFocus();
  });

  it('renders token preview pills for structured tokens', async () => {
    render(<Omnibox initialValue="cam:CAM-03 score:>80" onSearch={vi.fn()} />);
    expect(screen.getByText('camera:')).toBeInTheDocument();
    expect(screen.getByText('CAM-03')).toBeInTheDocument();
    expect(screen.getByText('score:')).toBeInTheDocument();
    expect(screen.getByText('>80')).toBeInTheDocument();
  });
});
