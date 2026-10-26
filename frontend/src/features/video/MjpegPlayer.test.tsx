import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MjpegPlayer } from './MjpegPlayer';

describe('MjpegPlayer Component', () => {
  it('renders connecting state initially', () => {
    render(<MjpegPlayer src="http://localhost:8001/cam/CAM-01.mjpg" label="CAM-01" />);
    expect(screen.getByText(/CONNECTING/i)).toBeInTheDocument();
  });

  it('switches to LIVE state when img onload fires', () => {
    const handleState = vi.fn();
    render(
      <MjpegPlayer
        src="http://localhost:8001/cam/CAM-01.mjpg"
        label="CAM-01"
        onStateChange={handleState}
      />
    );

    const img = screen.getByRole('img');
    fireEvent.load(img);

    expect(screen.getByText(/LIVE/i)).toBeInTheDocument();
    expect(handleState).toHaveBeenCalledWith('live');
  });

  it('releases connection by setting blank gif on unmount', () => {
    const { unmount } = render(
      <MjpegPlayer src="http://localhost:8001/cam/CAM-01.mjpg" label="CAM-01" />
    );
    const img = screen.getByRole('img') as HTMLImageElement;
    expect(img.src).toContain('/cam/CAM-01.mjpg');

    unmount();
    expect(img.src).toMatch(/^data:image\/gif/);
  });
});
