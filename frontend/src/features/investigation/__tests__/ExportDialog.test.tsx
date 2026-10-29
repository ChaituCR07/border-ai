import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExportDialog } from '../ExportDialog.js';

describe('ExportDialog component', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <ExportDialog isOpen={false} onClose={vi.fn()} state={{}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('enforces required purpose (min 5 characters) before downloading', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    const handleClose = vi.fn();

    render(
      <ExportDialog
        isOpen={true}
        onClose={handleClose}
        state={{ camera_id: ['CAM-01'] }}
      />
    );

    const submitBtn = screen.getByRole('button', { name: /download csv/i });
    const textarea = screen.getByRole('textbox', { name: /investigative purpose/i });

    // Try submitting empty purpose
    await userEvent.click(submitBtn);
    expect(openSpy).not.toHaveBeenCalled();

    // Type short purpose (< 5 chars)
    await userEvent.type(textarea, 'test');
    await userEvent.click(submitBtn);
    expect(screen.getByText(/minimum 5 characters/i)).toBeInTheDocument();
    expect(openSpy).not.toHaveBeenCalled();

    // Type valid purpose (>= 5 chars)
    await userEvent.type(textarea, ' - valid security incident investigation');
    await userEvent.click(submitBtn);

    expect(openSpy).toHaveBeenCalledTimes(1);
    const url = openSpy.mock.calls[0]?.[0];
    expect(url).toContain('/api/investigation/export.csv');
    expect(url).toContain('purpose=test');
    expect(handleClose).toHaveBeenCalledTimes(1);

    openSpy.mockRestore();
  });
});
