import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SeverityCounters } from './SeverityCounters';
import { useUIStore } from '../../state/uiStore';

function renderWithClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SeverityCounters />
    </QueryClientProvider>
  );
}

describe('SeverityCounters Component', () => {
  beforeEach(() => {
    useUIStore.setState({ severityFilter: null });
  });

  it('renders all 4 severity tiles with labels and icons', async () => {
    renderWithClient();
    expect(screen.getByText(/critical/i)).toBeInTheDocument();
    expect(screen.getByText(/high/i)).toBeInTheDocument();
    expect(screen.getByText(/medium/i)).toBeInTheDocument();
    expect(screen.getByText(/low/i)).toBeInTheDocument();
  });

  it('displays API counts for open alerts after MSW loads', async () => {
    renderWithClient();
    await waitFor(() => {
      expect(screen.getByTestId('count-CRITICAL')).toHaveTextContent('2');
      expect(screen.getByTestId('count-HIGH')).toHaveTextContent('7');
      expect(screen.getByTestId('count-MEDIUM')).toHaveTextContent('21');
      expect(screen.getByTestId('count-LOW')).toHaveTextContent('84');
    });
  });

  it('toggles filter on click and reflects aria-pressed state', async () => {
    const user = userEvent.setup();
    renderWithClient();

    const critBtn = await screen.findByRole('button', { name: /critical alerts/i });
    expect(critBtn).toHaveAttribute('aria-pressed', 'false');

    await user.click(critBtn);
    expect(critBtn).toHaveAttribute('aria-pressed', 'true');
    expect(useUIStore.getState().severityFilter).toBe('CRITICAL');

    await user.click(critBtn);
    expect(critBtn).toHaveAttribute('aria-pressed', 'false');
    expect(useUIStore.getState().severityFilter).toBeNull();
  });
});
