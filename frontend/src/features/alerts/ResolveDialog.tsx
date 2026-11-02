import React, { useState } from 'react';

export type ResolutionChoice = 'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'DUPLICATE' | 'OTHER';

interface ResolveDialogProps {
  alertId: string;
  isOpen: boolean;
  onClose: () => void;
  onResolved: (resolution: ResolutionChoice, note?: string) => void;
}

export const ResolveDialog: React.FC<ResolveDialogProps> = ({
  alertId,
  isOpen,
  onClose,
  onResolved,
}) => {
  const [resolution, setResolution] = useState<ResolutionChoice>('FALSE_POSITIVE');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const res = await fetch(`/api/alerts/${encodeURIComponent(alertId)}/resolve`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          resolution,
          note: note.trim() ? note.trim() : undefined,
        }),
      });

      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(json.error?.message || `Failed to resolve alert: ${res.status}`);
      }

      onResolved(resolution, note.trim() ? note.trim() : undefined);
      onClose();
    } catch (err: any) {
      setError(err.message || 'An error occurred during alert resolution.');
    } finally {
      setSubmitting(false);
    }
  };

  const maxNoteLen = 500;
  const remainingChars = maxNoteLen - note.length;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="resolve-dialog-title"
      className="fixed inset-0 z-60 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-[var(--bg-panel)] border border-[var(--border)] rounded-lg p-5 shadow-2xl flex flex-col gap-4 text-xs"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
          <h2 id="resolve-dialog-title" className="text-sm font-bold text-[var(--text)]">
            Resolve Threat Alert
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="text-[var(--text-muted)] hover:text-[var(--text)] cursor-pointer text-base"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)] mb-2">
              Resolution Disposition
            </label>
            <div className="space-y-2">
              <label className="flex items-center gap-2.5 p-2 rounded border border-[var(--border)] bg-[var(--bg-panel-2)] hover:border-[var(--border-focus)] cursor-pointer">
                <input
                  type="radio"
                  name="resolution"
                  value="FALSE_POSITIVE"
                  checked={resolution === 'FALSE_POSITIVE'}
                  onChange={() => setResolution('FALSE_POSITIVE')}
                  className="accent-[var(--ok)]"
                />
                <div>
                  <div className="font-semibold text-[var(--text)]">False Positive</div>
                  <div className="text-[10px] text-[var(--text-dim)]">Benign detection or misclassification</div>
                </div>
              </label>

              <label className="flex items-center gap-2.5 p-2 rounded border border-[var(--border)] bg-[var(--bg-panel-2)] hover:border-[var(--border-focus)] cursor-pointer">
                <input
                  type="radio"
                  name="resolution"
                  value="TRUE_POSITIVE"
                  checked={resolution === 'TRUE_POSITIVE'}
                  onChange={() => setResolution('TRUE_POSITIVE')}
                  className="accent-[var(--warn)]"
                />
                <div>
                  <div className="font-semibold text-[var(--text)]">True Positive</div>
                  <div className="text-[10px] text-[var(--text-dim)]">Confirmed security threat verified by personnel</div>
                </div>
              </label>

              <label className="flex items-center gap-2.5 p-2 rounded border border-[var(--border)] bg-[var(--bg-panel-2)] hover:border-[var(--border-focus)] cursor-pointer">
                <input
                  type="radio"
                  name="resolution"
                  value="DUPLICATE"
                  checked={resolution === 'DUPLICATE'}
                  onChange={() => setResolution('DUPLICATE')}
                  className="accent-[var(--border-focus)]"
                />
                <div>
                  <div className="font-semibold text-[var(--text)]">Duplicate Alert</div>
                  <div className="text-[10px] text-[var(--text-dim)]">Redundant alert for an already handled incident</div>
                </div>
              </label>

              <label className="flex items-center gap-2.5 p-2 rounded border border-[var(--border)] bg-[var(--bg-panel-2)] hover:border-[var(--border-focus)] cursor-pointer">
                <input
                  type="radio"
                  name="resolution"
                  value="OTHER"
                  checked={resolution === 'OTHER'}
                  onChange={() => setResolution('OTHER')}
                  className="accent-[var(--border-focus)]"
                />
                <div>
                  <div className="font-semibold text-[var(--text)]">Other Resolution</div>
                  <div className="text-[10px] text-[var(--text-dim)]">Routine patrol clearance or administrative handoff</div>
                </div>
              </label>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label htmlFor="resolve-note" className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-muted)]">
                Resolution Note (Optional)
              </label>
              <span className={`text-[10px] font-mono ${remainingChars < 50 ? 'text-amber-400' : 'text-[var(--text-dim)]'}`}>
                {remainingChars} chars left
              </span>
            </div>
            <textarea
              id="resolve-note"
              value={note}
              maxLength={maxNoteLen}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Provide context or patrol log reference (never emailed, internal audit only)..."
              rows={3}
              className="w-full p-2 rounded bg-[var(--bg-panel-2)] border border-[var(--border)] text-[var(--text)] focus:outline-hidden focus:border-[var(--border-focus)] text-xs resize-none"
            />
          </div>

          {error && (
            <div role="alert" className="p-2 rounded bg-rose-950/70 border border-rose-600/70 text-rose-200 text-[11px]">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t border-[var(--border)]">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded border border-[var(--border)] bg-[var(--bg-panel-2)] hover:bg-[var(--bg-panel-hover)] text-[var(--text)] font-semibold cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold cursor-pointer disabled:opacity-50 transition-colors"
            >
              {submitting ? 'Resolving...' : 'Confirm Resolution'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
