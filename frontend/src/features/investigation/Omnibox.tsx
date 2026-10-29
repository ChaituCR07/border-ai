import React, { useState, useEffect, useRef, useCallback } from 'react';
import { parseOmniboxQuery, type ParsedQuery } from './queryParser.js';

interface SuggestItem {
  value: string;
  count: number;
  last_seen: string;
}

interface OmniboxProps {
  initialValue?: string;
  onSearch: (parsed: ParsedQuery) => void;
  className?: string;
}

export const Omnibox: React.FC<OmniboxProps> = ({
  initialValue = '',
  onSearch,
  className = '',
}) => {
  const [text, setText] = useState(initialValue);
  const [suggestions, setSuggestions] = useState<SuggestItem[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setText(initialValue);
  }, [initialValue]);

  // Global '/' keyboard shortcut to focus omnibox
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== inputRef.current) {
        const tagName = document.activeElement?.tagName;
        if (tagName !== 'INPUT' && tagName !== 'TEXTAREA') {
          e.preventDefault();
          inputRef.current?.focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Fetch suggestions on prefix typing with debounce
  useEffect(() => {
    const trimmed = text.trim();
    if (!trimmed || trimmed.length < 2) {
      setSuggestions([]);
      return;
    }

    const timer = setTimeout(async () => {
      let kind = 'plate';
      let prefix = trimmed;

      if (prefix.toLowerCase().startsWith('cam:')) {
        kind = 'camera';
        prefix = prefix.slice(4).trim();
      } else if (prefix.toLowerCase().startsWith('camera:')) {
        kind = 'camera';
        prefix = prefix.slice(7).trim();
      } else if (prefix.toLowerCase().startsWith('person:') || prefix.toLowerCase().startsWith('per:')) {
        kind = 'person';
        prefix = prefix.replace(/^(person:|per:)/i, '').trim();
      }

      if (!prefix || (kind === 'person' && prefix.length < 3) || prefix.length < 2) {
        setSuggestions([]);
        return;
      }

      try {
        setLoadingSuggestions(true);
        const res = await fetch(`/api/investigation/suggest?kind=${kind}&prefix=${encodeURIComponent(prefix)}`);
        if (res.ok) {
          const json = await res.json();
          setSuggestions(json.data || []);
        }
      } catch {
        // Ignore network or abort errors in suggestions
      } finally {
        setLoadingSuggestions(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [text]);

  const handleSubmit = useCallback((e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setShowSuggestions(false);
    const parsed = parseOmniboxQuery(text);
    onSearch(parsed);
  }, [text, onSearch]);

  const handleSelectSuggestion = (s: SuggestItem) => {
    let newText = s.value;
    if (text.toLowerCase().startsWith('cam:')) {
      newText = `cam:${s.value}`;
    } else if (text.toLowerCase().startsWith('person:') || text.toLowerCase().startsWith('per:')) {
      newText = `person:${s.value}`;
    }
    setText(newText);
    setShowSuggestions(false);
    const parsed = parseOmniboxQuery(newText);
    onSearch(parsed);
  };

  const parsed = parseOmniboxQuery(text);

  return (
    <div className={`relative w-full ${className}`}>
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <div className="relative flex-1 flex items-center bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 focus-within:border-sky-500 focus-within:ring-1 focus-within:ring-sky-500">
          <svg
            className="w-5 h-5 text-slate-400 mr-2 shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>

          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded={showSuggestions && suggestions.length > 0}
            aria-autocomplete="list"
            aria-label="Investigation search omnibox"
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            placeholder="Search events, plates (KA01*), cam:CAM-01, type:VEHICLE, sev:CRITICAL... [/ to focus]"
            className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm focus:outline-none"
          />

          {text && (
            <button
              type="button"
              onClick={() => {
                setText('');
                setSuggestions([]);
                onSearch({ tokens: [], freeText: '', state: {} });
              }}
              aria-label="Clear search input"
              className="text-slate-400 hover:text-slate-200 ml-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}

          <kbd className="hidden sm:inline-block ml-2 px-1.5 py-0.5 text-xs text-slate-400 bg-slate-800 border border-slate-700 rounded">
            /
          </kbd>
        </div>

        <button
          type="submit"
          className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-sm font-medium rounded-lg transition-colors shrink-0"
        >
          Search
        </button>
      </form>

      {/* Token preview pills */}
      {parsed.tokens.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {parsed.tokens.map((token, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-200 border border-slate-700"
            >
              <span className="text-slate-400 font-medium">{token.key}:</span>
              <span>{token.value}</span>
            </span>
          ))}
          {parsed.freeText && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-800/60 text-slate-300 border border-slate-700/60">
              text: "{parsed.freeText}"
            </span>
          )}
        </div>
      )}

      {/* Autocomplete suggestions dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <ul
          role="listbox"
          className="absolute z-20 left-0 right-0 mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl max-h-60 overflow-y-auto divide-y divide-slate-800"
        >
          {suggestions.map((s, idx) => (
            <li
              key={idx}
              role="option"
              aria-selected={false}
              onClick={() => handleSelectSuggestion(s)}
              className="px-3 py-2 hover:bg-slate-800 cursor-pointer flex items-center justify-between text-sm"
            >
              <span className="text-sky-300 font-mono font-medium">{s.value}</span>
              <span className="text-xs text-slate-400">
                {s.count} events · seen {new Date(s.last_seen).toLocaleDateString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
