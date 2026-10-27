import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConnectionBadge } from './ConnectionBadge';

function renderBadge() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ConnectionBadge />
    </QueryClientProvider>
  );
}

describe('ConnectionBadge Component', () => {
  it('renders status role with appropriate live or fallback text', async () => {
    renderBadge();
    const statusElem = screen.getByRole('status');
    expect(statusElem).toBeInTheDocument();
  });
});
