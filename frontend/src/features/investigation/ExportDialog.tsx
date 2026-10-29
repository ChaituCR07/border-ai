import React, { useState } from 'react';
import { serializeSearchParams, type InvestigationSearchState } from './searchSchema.js';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  state: InvestigationSearchState;
}

export const ExportDialog: React.FC<ExportDialogProps> = ({
  isOpen,
  onClose,
  state,
}) => {
  const [purpose, setPurpose] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDownload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!purpose.trim() || purpose.trim().length < 5) {
      setError('An explicit investigative purpose (minimum 5 characters) is required.');
      return;
    }

    const params = serializeSearchParams(state);
    params.set('purpose', purpose.trim());

    const exportUrl = `/api/investigation/export.csv?${params.toString()}`;
    window.open(exportUrl, '_blank');
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-xs"
    >
      <div className="w-full max-w-md bg-slate-900 border border-slate-750 rounded-xl p-5 shadow-2xl space-y-4 text-slate-100">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <h2 id="export-dialog-title" className="text-base font-bold text-slate-100 flex items-center gap-2">
            <svg className="w-5 h-5 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export Forensic Event Data
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close export dialog"
            className="text-slate-400 hover:text-slate-100"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-3 bg-amber-950/30 border border-amber-800/40 rounded-lg text-xs text-amber-200/90 leading-relaxed">
          <span className="font-semibold text-amber-300">Audited Operation:</span> In compliance with border data retention and privacy policies (ADR 0024), all CSV exports are logged with your user identifier, IP, query filters, and stated purpose.
        </div>

        <form onSubmit={handleDownload} className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="export-purpose" className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Investigative Purpose <span className="text-red-400">*</span>
            </label>
            <textarea
              id="export-purpose"
              rows={3}
              value={purpose}
              onChange={(e) => {
                setPurpose(e.target.value);
                if (error) setError(null);
              }}
              placeholder="e.g. Case #2026-881: Suspected border breach correlation and evidence package"
              className="w-full text-xs p-2.5 bg-slate-950 border border-slate-750 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500"
              required
            />
            {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
          </div>

          <div className="text-[11px] text-slate-500">
            Export format: UTF-8 CSV with formula injection sanitization. Hard capped at 10,000 rows.
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded-lg text-xs font-medium bg-sky-600 hover:bg-sky-500 text-white transition-colors"
            >
              Download CSV
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
