import React, { useState } from 'react';
import type { Anomaly } from './types.js';

export interface AnomalyListProps {
  anomalies: Anomaly[];
  className?: string;
}

export const AnomalyList: React.FC<AnomalyListProps> = ({ anomalies, className = '' }) => {
  const [hintsOpen, setHintsOpen] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const warnings = anomalies.filter((a) => a.severity === 'warning');
  const hints = anomalies.filter((a) => a.severity === 'info');

  const copyMessage = (msg: string, idx: number) => {
    navigator.clipboard.writeText(msg).catch(() => {});
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 1500);
  };

  if (anomalies.length === 0) {
    return (
      <div
        className={`anomaly-list ${className}`}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          background: 'var(--bg-panel-2, #18212c)',
          borderRadius: 'var(--radius-sm, 6px)',
          fontSize: '0.85rem',
          color: 'var(--ok, #2ecc71)',
        }}
      >
        <span style={{ fontWeight: 600 }}>Findings (0)</span>
        <span>✓ No anomalies</span>
      </div>
    );
  }

  return (
    <div
      className={`anomaly-list ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--text, #e6edf3)' }}>
          Findings ({anomalies.length})
        </span>
      </div>

      {/* Warnings List */}
      {warnings.map((w, i) => (
        <div
          key={`warn-${i}`}
          role="alert"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
            padding: '8px 12px',
            background: 'var(--sev-high-bg, rgba(255, 159, 26, 0.15))',
            border: '1px solid var(--sev-high, #ff9f1a)',
            borderRadius: 'var(--radius-sm, 6px)',
            fontSize: '0.8rem',
            color: 'var(--text, #e6edf3)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--sev-high, #ff9f1a)' }}>⚠</span>
            <span>{w.message}</span>
          </div>

          <button
            type="button"
            onClick={() => copyMessage(w.message, i)}
            aria-label="Copy anomaly message"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted, #93a1b2)',
              cursor: 'pointer',
              fontSize: '0.75rem',
              padding: '2px 6px',
            }}
          >
            {copiedIndex === i ? 'Copied' : 'Copy'}
          </button>
        </div>
      ))}

      {/* Info / Hints List Accordion */}
      {hints.length > 0 && (
        <div style={{ marginTop: '2px' }}>
          <button
            type="button"
            onClick={() => setHintsOpen((prev) => !prev)}
            aria-expanded={hintsOpen}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted, #93a1b2)',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 500,
              padding: '4px 0',
            }}
          >
            <span>{hintsOpen ? '▼' : '▶'}</span>
            <span>Hints ({hints.length})</span>
          </button>

          {hintsOpen && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
              {hints.map((h, i) => (
                <div
                  key={`hint-${i}`}
                  style={{
                    padding: '6px 10px',
                    background: 'var(--bg-panel-2, #18212c)',
                    border: '1px solid var(--border-muted, #1c2633)',
                    borderRadius: 'var(--radius-sm, 6px)',
                    fontSize: '0.78rem',
                    color: 'var(--text-muted, #93a1b2)',
                  }}
                >
                  ℹ {h.message}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

