import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AlertFeed } from './AlertFeed';
import { useUIStore } from '../../state/uiStore';

function renderWithClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AlertFeed />
    </QueryClientProvider>
  );
}

describe('AlertFeed Component', () => {
  beforeEach(() => {
    useUIStore.setState({
      severityFilter: null,
      selectedCameraId: null,
      selectedCameraOnly: false,
    });
  });

  it('renders open alerts feed with MSW mock alerts', async () => {
    renderWithClient();
    expect(screen.getByText(/open alerts/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('RESTRICTED ZONE ENTRY')).toBeInTheDocument();
      expect(screen.getByText('ANPR WATCHLIST HIT')).toBeInTheDocument();
    });
  });

  it('optimistically removes alert when Acknowledge is clicked', async () => {
    const user = userEvent.setup();
    renderWithClient();

    const ackButtons = await screen.findAllByRole('button', { name: /^acknowledge$/i });
    expect(ackButtons.length).toBeGreaterThan(0);

    const firstAck = ackButtons[0]!;
    await user.click(firstAck);

    await waitFor(() => {
      // First card (RESTRICTED ZONE ENTRY) is optimistically removed
      expect(screen.queryByText('RESTRICTED ZONE ENTRY')).not.toBeInTheDocument();
    });
  });
});
