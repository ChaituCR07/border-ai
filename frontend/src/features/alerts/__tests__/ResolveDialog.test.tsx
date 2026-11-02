import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ResolveDialog } from '../ResolveDialog';

describe('ResolveDialog Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <ResolveDialog
        alertId="alt-001"
        isOpen={false}
        onClose={vi.fn()}
        onResolved={vi.fn()}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders dialog elements and radio buttons when open', () => {
    render(
      <ResolveDialog
        alertId="alt-001"
        isOpen={true}
        onClose={vi.fn()}
        onResolved={vi.fn()}
      />
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Resolve Threat Alert')).toBeInTheDocument();
    expect(screen.getByLabelText(/false positive/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/true positive/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/duplicate/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/other resolution/i)).toBeInTheDocument();
  });

  it('submits resolution and calls onResolved callback', async () => {
    const user = userEvent.setup();
    const onResolved = vi.fn();
    const onClose = vi.fn();

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: { status: 'RESOLVED', resolution: 'TRUE_POSITIVE' } }),
    } as any);

    render(
      <ResolveDialog
        alertId="alt-001"
        isOpen={true}
        onClose={onClose}
        onResolved={onResolved}
      />
    );

    // Select True Positive radio
    const verifiedRadio = screen.getByLabelText(/true positive/i);
    await user.click(verifiedRadio);

    // Type optional note
    const noteTextarea = screen.getByPlaceholderText(/provide context/i);
    await user.type(noteTextarea, 'Patrol intercepted suspicious vehicle at checkpoint.');

    // Click confirm resolution
    const confirmBtn = screen.getByRole('button', { name: /confirm resolution/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/alerts/alt-001/resolve',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({
            resolution: 'TRUE_POSITIVE',
            note: 'Patrol intercepted suspicious vehicle at checkpoint.',
          }),
        })
      );
      expect(onResolved).toHaveBeenCalledWith(
        'TRUE_POSITIVE',
        'Patrol intercepted suspicious vehicle at checkpoint.'
      );
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('displays error message when endpoint responds with an error', async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: { message: 'Alert is already resolved' } }),
    } as any);

    render(
      <ResolveDialog
        alertId="alt-001"
        isOpen={true}
        onClose={vi.fn()}
        onResolved={vi.fn()}
      />
    );

    const confirmBtn = screen.getByRole('button', { name: /confirm resolution/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Alert is already resolved');
    });
  });
});
