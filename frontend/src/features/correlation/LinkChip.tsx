import React, { useState, useRef, useEffect } from 'react';
import type { Link, LinkClass } from './types.js';

export interface LinkChipProps {
  link: Link;
  className?: string;
}

const CLASS_CONFIG: Record<
  LinkClass,
  { icon: string; label: string; bgVar: string; borderVar: string; textVar: string }
> = {
  PLAUSIBLE: {
    icon: '✓',
    label: 'PLAUSIBLE',
    bgVar: 'var(--link-ok-bg, rgba(16, 185, 129, 0.15))',
    borderVar: 'var(--link-ok, #10b981)',
    textVar: 'var(--link-ok, #10b981)',
  },
  FAST: {
    icon: '⚠',
    label: 'FAST',
    bgVar: 'var(--link-warn-bg, rgba(245, 158, 11, 0.15))',
    borderVar: 'var(--link-warn, #f59e0b)',
    textVar: 'var(--link-warn, #f59e0b)',
  },
  SLOW: {
    icon: '⚠',
    label: 'SLOW',
    bgVar: 'var(--link-warn-bg, rgba(245, 158, 11, 0.15))',
    borderVar: 'var(--link-warn, #f59e0b)',
    textVar: 'var(--link-warn, #f59e0b)',
  },
  IMPOSSIBLE: {
    icon: '✕',
    label: 'IMPOSSIBLE',
    bgVar: 'var(--link-bad-bg, rgba(239, 68, 68, 0.15))',
    borderVar: 'var(--link-bad, #ef4444)',
    textVar: 'var(--link-bad, #ef4444)',
  },
  SIMULTANEOUS: {
    icon: '✕',
    label: 'SIMULTANEOUS',
    bgVar: 'var(--link-bad-bg, rgba(239, 68, 68, 0.15))',
    borderVar: 'var(--link-bad, #ef4444)',
    textVar: 'var(--link-bad, #ef4444)',
  },
  OVERLAP_OK: {
    icon: '✓',
    label: 'OVERLAP',
    bgVar: 'var(--link-ok-bg, rgba(16, 185, 129, 0.15))',
    borderVar: 'var(--link-ok, #10b981)',
    textVar: 'var(--link-ok, #10b981)',
  },
  REVISIT: {
    icon: '↺',
    label: 'REVISIT',
    bgVar: 'var(--link-ok-bg, rgba(16, 185, 129, 0.15))',
    borderVar: 'var(--link-ok, #10b981)',
    textVar: 'var(--link-ok, #10b981)',
  },
  UNLINKED: {
    icon: '?',
    label: 'UNLINKED',
    bgVar: 'var(--link-unknown-bg, rgba(107, 114, 128, 0.15))',
    borderVar: 'var(--link-unknown, #6b7280)',
    textVar: 'var(--link-unknown, #6b7280)',
  },
};

export const LinkChip: React.FC<LinkChipProps> = ({ link, className = '' }) => {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const conf = CLASS_CONFIG[link.class] ?? CLASS_CONFIG.UNLINKED;

  const percent = Math.round(link.confidence * 100);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  return (
    <div
      ref={containerRef}
      className={`link-chip-container ${className}`}
      style={{ position: 'relative', display: 'inline-block' }}
      onBlur={(e) => {
        if (!containerRef.current?.contains(e.relatedTarget as Node)) {
          setOpen(false);
        }
      }}
    >
      <div
        role="button"
        tabIndex={0}
        aria-expanded={open}
        aria-label={`Link ${link.from_camera} to ${link.to_camera}: ${link.class} ${percent}%`}
        data-class={link.class}
        onClick={() => setOpen((prev) => !prev)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setOpen((prev) => !prev);
          }
        }}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '2px 8px',
          borderRadius: '12px',
          fontSize: '0.75rem',
          fontWeight: 600,
          cursor: 'pointer',
          background: conf.bgVar,
          border: `1px solid ${conf.borderVar}`,
          color: conf.textVar,
          userSelect: 'none',
        }}
      >
        <span aria-hidden="true">{conf.icon}</span>
        <span>{conf.label}</span>
        <span style={{ opacity: 0.9 }}>{percent}%</span>
      </div>

      {open && (
        <div
          role="dialog"
          aria-label="Link Factor Breakdown"
          style={{
            position: 'absolute',
            bottom: 'calc(100% + 6px)',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--bg-panel-2, #18212c)',
            border: '1px solid var(--border, #243041)',
            borderRadius: 'var(--radius-sm, 6px)',
            padding: '10px 12px',
            fontSize: '0.75rem',
            color: 'var(--text, #e6edf3)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            zIndex: 100,
            minWidth: '220px',
            maxWidth: '300px',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '6px', borderBottom: '1px solid var(--border-muted, #1c2633)', paddingBottom: '4px' }}>
            {link.from_camera} → {link.to_camera} ({link.gap_s}s)
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {link.factors.map((f, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                <span style={{ color: 'var(--text-muted, #93a1b2)', textTransform: 'capitalize' }}>{f.name}:</span>
                <span style={{ textAlign: 'right' }}>
                  {Math.round(f.value * 100)}% ({f.detail})
                </span>
              </div>
            ))}

            {link.expected && (
              <div style={{ marginTop: '4px', paddingTop: '4px', borderTop: '1px dotted var(--border-muted, #1c2633)' }}>
                <span style={{ color: 'var(--text-muted, #93a1b2)' }}>Expected:</span>{' '}
                <span>{link.expected.min_s}s – {link.expected.max_s}s (typ {link.expected.typical_s}s)</span>
              </div>
            )}

            {link.missed_cameras.length > 0 && (
              <div style={{ marginTop: '4px', color: 'var(--warn, #f5a623)' }}>
                ⚠ Missed camera(s): {link.missed_cameras.join(', ')}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

