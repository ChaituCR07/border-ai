import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled UI exception in ErrorBoundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center p-6 bg-[var(--bg-panel)] rounded-[var(--radius)] border border-[var(--sev-critical)] text-center">
          <span className="text-3xl mb-2">💥</span>
          <h3 className="text-sm font-bold text-[var(--sev-critical)]">
            {this.props.fallbackTitle ?? 'Component Failure'}
          </h3>
          <p className="text-xs text-[var(--text-muted)] mt-1 max-w-sm">
            {this.state.error?.message || 'An unexpected rendering error occurred.'}
          </p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-3 px-3 py-1 text-xs rounded bg-[var(--bg-panel-2)] hover:bg-[var(--border)] text-[var(--text)] border border-[var(--border)] transition-colors cursor-pointer"
          >
            Retry Component
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
