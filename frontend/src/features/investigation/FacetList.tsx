import React, { useState } from 'react';

interface FacetItem {
  value: string;
  count: number;
}

interface FacetListProps {
  title: string;
  items: FacetItem[];
  selected: string[];
  onChange: (selected: string[]) => void;
  maxVisible?: number;
  className?: string;
}

export const FacetList: React.FC<FacetListProps> = ({
  title,
  items,
  selected,
  onChange,
  maxVisible = 6,
  className = '',
}) => {
  const [expanded, setExpanded] = useState(false);
  const [filterText, setFilterText] = useState('');

  const filteredItems = items.filter(item =>
    item.value.toLowerCase().includes(filterText.toLowerCase())
  );

  const visibleItems = expanded ? filteredItems : filteredItems.slice(0, maxVisible);

  const toggleItem = (val: string) => {
    if (selected.includes(val)) {
      onChange(selected.filter(x => x !== val));
    } else {
      onChange([...selected, val]);
    }
  };

  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className="flex items-center justify-between text-xs font-semibold text-slate-300 uppercase tracking-wider">
        <span>{title}</span>
        {selected.length > 0 && (
          <button
            type="button"
            onClick={() => onChange([])}
            className="text-sky-400 hover:text-sky-300 text-xs lowercase"
          >
            clear
          </button>
        )}
      </div>

      {items.length > maxVisible && (
        <input
          type="text"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          placeholder={`Filter ${title.toLowerCase()}...`}
          className="w-full text-xs px-2 py-1 bg-slate-900 border border-slate-750 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
        />
      )}

      <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
        {visibleItems.length === 0 ? (
          <div className="text-xs text-slate-500 italic py-1">No items found</div>
        ) : (
          visibleItems.map((item) => {
            const isChecked = selected.includes(item.value);
            return (
              <label
                key={item.value}
                className="flex items-center justify-between text-xs text-slate-300 hover:text-slate-100 cursor-pointer py-0.5 rounded px-1 hover:bg-slate-800/60"
              >
                <div className="flex items-center gap-1.5 truncate">
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => toggleItem(item.value)}
                    className="rounded border-slate-700 bg-slate-900 text-sky-500 focus:ring-0 focus:ring-offset-0"
                  />
                  <span className="truncate font-mono">{item.value}</span>
                </div>
                <span className="text-slate-500 ml-2 font-mono tabular-nums">{item.count}</span>
              </label>
            );
          })
        )}
      </div>

      {filteredItems.length > maxVisible && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-sky-400 hover:text-sky-300 font-medium pt-0.5"
        >
          {expanded ? 'Show less' : `Show all (${filteredItems.length})`}
        </button>
      )}
    </div>
  );
};
