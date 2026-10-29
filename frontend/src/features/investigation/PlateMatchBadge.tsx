import React from 'react';
import type { PlateMatch } from './searchSchema.js';

interface PlateMatchBadgeProps {
  match?: PlateMatch | string | null;
  className?: string;
}

export const PlateMatchBadge: React.FC<PlateMatchBadgeProps> = ({ match, className = '' }) => {
  if (!match || match === 'exact' || match === 'none') {
    return null;
  }

  let label = '';
  let colorClasses = '';
  let title = '';

  switch (match) {
    case 'lookalike':
      label = 'Look-alike';
      colorClasses = 'bg-amber-900/40 text-amber-300 border-amber-600/50';
      title = 'Matches OCR confusable characters (e.g. 0/O, 1/I, 8/B, 5/S)';
      break;
    case 'prefix':
      label = 'Prefix';
      colorClasses = 'bg-sky-900/40 text-sky-300 border-sky-600/50';
      title = 'Matches plates starting with this prefix';
      break;
    case 'contains':
    case 'partial':
      label = 'Partial';
      colorClasses = 'bg-purple-900/40 text-purple-300 border-purple-600/50';
      title = 'Matches plates containing this substring';
      break;
    default:
      label = String(match);
      colorClasses = 'bg-slate-800 text-slate-300 border-slate-600/50';
  }

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium border ${colorClasses} ${className}`}
      title={title}
      data-testid="plate-match-badge"
    >
      {label}
    </span>
  );
};
