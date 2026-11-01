import React, { useState } from 'react';
import { useSequenceSearch } from './api.js';
import type { SequenceMatch } from './types.js';

export interface SequenceSearchProps {
  from?: string;
  to?: string;
  onSelectPlate?: (plate: string) => void;
  className?: string;
}

export const SequenceSearch: React.FC<SequenceSearchProps> = ({
  from,
  to,
  onSelectPlate,
  className = '',
}) => {
  const [collapsed, setCollapsed] = useState(true);
  const [steps, setSteps] = useState<string[]>(['CAM-01', 'CAM-02', 'CAM-04']);
  const [maxHopGapS, setMaxHopGapS] = useState(900);
  const [purpose, setPurpose] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState<{
    cams: string;
    from: string;
    to: string;
    max_hop_gap_s: number;
    purpose: string;
  } | null>(null);

  const actualFrom = from ?? new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  const actualTo = to ?? new Date().toISOString();

  const { data, isLoading, isError, error } = useSequenceSearch(
    submittedQuery ?? {
      cams: '',
      from: '',
      to: '',
      purpose: '',
    },
    { enabled: submittedQuery !== null }
  );

  const handleAddStep = () => {
    if (steps.length < 5) {
      setSteps([...steps, `CAM-0${steps.length + 1}`]);
    }
  };

  const handleRemoveStep = (idx: number) => {
    if (steps.length > 2) {
      setSteps(steps.filter((_, i) => i !== idx));
    }
  };

  const handleStepChange = (idx: number, val: string) => {
    const updated = [...steps];
    updated[idx] = val.trim().toUpperCase();
    setSteps(updated);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (purpose.trim().length < 5 || steps.length < 2) return;

    setSubmittedQuery({
      cams: steps.join(','),
      from: actualFrom,
      to: actualTo,
      max_hop_gap_s: maxHopGapS,
      purpose: purpose.trim(),
    });
  };

  const matches = data?.data ?? [];

  return (
    <div
      className={`sequence-search-panel ${className}`}
      style={{
        background: 'var(--bg-panel, #121821)',
        borderRadius: 'var(--radius, 10px)',
        border: '1px solid var(--border, #243041)',
        overflow: 'hidden',
      }}
    >
      {/* Header Accordion Toggle */}
      <button
        type="button"
        onClick={() => setCollapsed((prev) => !prev)}
        aria-expanded={!collapsed}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          background: 'var(--bg-panel-2, #18212c)',
          border: 'none',
          color: 'var(--text, #e6edf3)',
          cursor: 'pointer',
          fontSize: '0.85rem',
          fontWeight: 600,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>{collapsed ? '▶' : '▼'}</span>
          <span>Path pattern search (multi-camera sequence)</span>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #93a1b2)', fontWeight: 400 }}>
          {collapsed ? 'Expand to query convoy paths' : 'Investigator / Admin'}
        </span>
      </button>

      {!collapsed && (
        <form onSubmit={handleSearch} style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Steps inputs */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted, #93a1b2)', marginBottom: '6px' }}>
              Camera Sequence ({steps.length} of 5 steps):
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              {steps.map((step, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {idx > 0 && <span style={{ color: 'var(--text-dim, #64748b)' }}>→</span>}
                  <input
                    type="text"
                    value={step}
                    onChange={(e) => handleStepChange(idx, e.target.value)}
                    placeholder="e.g. CAM-01"
                    aria-label={`Step ${idx + 1} camera`}
                    style={{
                      width: '90px',
                      background: 'var(--bg-app, #0b0f14)',
                      border: '1px solid var(--border, #243041)',
                      borderRadius: '4px',
                      padding: '4px 8px',
                      color: 'var(--text, #e6edf3)',
                      fontSize: '0.8rem',
                    }}
                  />
                  {steps.length > 2 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveStep(idx)}
                      aria-label={`Remove step ${idx + 1}`}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-dim, #64748b)',
                        cursor: 'pointer',
                        padding: '0 2px',
                      }}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}

              {steps.length < 5 && (
                <button
                  type="button"
                  onClick={handleAddStep}
                  style={{
                    background: 'var(--bg-panel-hover, #1f2c3b)',
                    border: '1px dashed var(--border, #243041)',
                    borderRadius: '4px',
                    color: 'var(--border-focus, #38bdf8)',
                    fontSize: '0.8rem',
                    padding: '4px 8px',
                    cursor: 'pointer',
                  }}
                >
                  + Add Step
                </button>
              )}
            </div>
          </div>

          {/* Options Row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <label htmlFor="max-hop-gap" style={{ fontSize: '0.8rem', color: 'var(--text-muted, #93a1b2)' }}>
                Max hop gap (s):
              </label>
              <input
                id="max-hop-gap"
                type="number"
                min={1}
                max={86400}
                value={maxHopGapS}
                onChange={(e) => setMaxHopGapS(Number(e.target.value))}
                style={{
                  width: '80px',
                  background: 'var(--bg-app, #0b0f14)',
                  border: '1px solid var(--border, #243041)',
                  borderRadius: '4px',
                  padding: '4px 6px',
                  color: 'var(--text, #e6edf3)',
                  fontSize: '0.8rem',
                }}
              />
            </div>
          </div>

          {/* Purpose Field (Mandatory) */}
          <div>
            <label htmlFor="seq-purpose" style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted, #93a1b2)', marginBottom: '4px' }}>
              Operational Purpose (required, min 5 chars — audited):
            </label>
            <input
              id="seq-purpose"
              type="text"
              required
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="e.g. Operation Nightfall lead follow-up"
              style={{
                width: '100%',
                background: 'var(--bg-app, #0b0f14)',
                border: '1px solid var(--border, #243041)',
                borderRadius: '4px',
                padding: '6px 10px',
                color: 'var(--text, #e6edf3)',
                fontSize: '0.8rem',
              }}
            />
          </div>

          {/* Submit */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim, #64748b)' }}>
              🔒 Pattern search queries are logged to the immutable audit trail.
            </span>

            <button
              type="submit"
              disabled={purpose.trim().length < 5 || steps.length < 2 || isLoading}
              style={{
                background: purpose.trim().length >= 5 ? 'var(--border-focus, #38bdf8)' : 'var(--bg-panel-hover, #1f2c3b)',
                color: purpose.trim().length >= 5 ? '#0b0f14' : 'var(--text-dim, #64748b)',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 16px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: purpose.trim().length >= 5 && !isLoading ? 'pointer' : 'not-allowed',
              }}
            >
              {isLoading ? 'Searching...' : 'Run Pattern Search'}
            </button>
          </div>

          {/* Results Display */}
          {isError && (
            <div style={{ color: 'var(--sev-critical, #ff4d4f)', fontSize: '0.8rem', padding: '6px 0' }}>
              Error: {(error as Error)?.message || 'Search failed'}
            </div>
          )}

          {submittedQuery && !isLoading && !isError && (
            <div style={{ marginTop: '8px', borderTop: '1px solid var(--border-muted, #1c2633)', paddingTop: '10px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text, #e6edf3)', marginBottom: '8px' }}>
                Matches Found ({matches.length})
              </div>

              {matches.length === 0 ? (
                <div style={{ color: 'var(--text-dim, #64748b)', fontSize: '0.78rem' }}>
                  No vehicles matched the camera sequence within the time window and max gap.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {matches.map((m: SequenceMatch) => (
                    <div
                      key={m.plate_key}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 10px',
                        background: 'var(--bg-panel-2, #18212c)',
                        border: '1px solid var(--border, #243041)',
                        borderRadius: '6px',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, color: 'var(--text, #e6edf3)' }}>
                            {m.representative_plate}
                          </span>
                          {m.plate_variants.length > 1 && (
                            <span style={{ fontSize: '0.72rem', color: 'var(--link-warn, #f59e0b)' }}>
                              ({m.plate_variants.join(', ')})
                            </span>
                          )}
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #93a1b2)' }}>
                            Duration: {m.total_duration_s}s
                          </span>
                        </div>

                        <div style={{ fontSize: '0.72rem', color: 'var(--text-dim, #64748b)' }}>
                          {m.hops.map((h, i) => (
                            <span key={i}>
                              {i > 0 && ' → '}
                              {h.camera_id} ({new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })})
                            </span>
                          ))}
                        </div>
                      </div>

                      {onSelectPlate && (
                        <button
                          type="button"
                          onClick={() => onSelectPlate(m.representative_plate)}
                          style={{
                            background: 'var(--bg-panel-hover, #1f2c3b)',
                            border: '1px solid var(--border-focus, #38bdf8)',
                            color: 'var(--border-focus, #38bdf8)',
                            borderRadius: '4px',
                            padding: '4px 10px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          View Journey
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </form>
      )}
    </div>
  );
};
