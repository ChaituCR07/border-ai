import React, { useState } from 'react';

export interface ConfidenceBadgeProps {
  confidence: number; // 0..1
  label?: string;
  details?: Array<{ name: string; value: number; detail: string }>;
  className?: string;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  label,
  details = [],
  className = '',
}) => {
  const [showPopover, setShowPopover] = useState(false);
  const percent = Math.round(confidence * 100);

  let color = 'var(--link-ok, #10b981)';
  let bg = 'var(--link-ok-bg, rgba(16, 185, 129, 0.15))';
  if (confidence < 0.5) {
    color = 'var(--link-bad, #ef4444)';
    bg = 'var(--link-bad-bg, rgba(239, 68, 68, 0.15))';
  } else if (confidence < 0.8) {
    color = 'var(--link-warn, #f59e0b)';
    bg = 'var(--link-warn-bg, rgba(245, 158, 11, 0.15))';
  }

  return (
    <div
      className={`confidence-badge-wrapper ${className}`}
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={() => setShowPopover(true)}
      onMouseLeave={() => setShowPopover(false)}
      onFocus={() => setShowPopover(true)}
      onBlur={() => setShowPopover(false)}
    >
      <span
        tabIndex={0}
        role="button"
        aria-label={`Confidence: ${percent}%`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '2px 8px',
          borderRadius: '10px',
          fontSize: '0.75rem',
          fontWeight: 700,
          background: bg,
          border: `1px solid ${color}`,
          color,
          cursor: details.length > 0 ? 'pointer' : 'default',
        }}
      >
        {label && <span style={{ opacity: 0.8, fontWeight: 500 }}>{label}:</span>}
        <span>{percent}%</span>
      </span>

      {showPopover && details.length > 0 && (
        <div
          role="tooltip"
          style={{
            position: 'absolute',
            bottom: 'calc(100% + 4px)',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--bg-panel-2, #18212c)',
            border: '1px solid var(--border, #243041)',
            borderRadius: '6px',
            padding: '8px 10px',
            fontSize: '0.72rem',
            color: 'var(--text, #e6edf3)',
            boxShadow: '0 6px 16px rgba(0,0,0,0.4)',
            zIndex: 110,
            whiteSpace: 'nowrap',
          }}
        >
          {details.map((d, i) => (
            <div key={i} style={{ display: 'flex', gap: '8px', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted, #93a1b2)', textTransform: 'capitalize' }}>{d.name}:</span>
              <span>{Math.round(d.value * 100)}% ({d.detail})</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
