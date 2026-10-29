import { useMemo, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  parseSearchParams,
  serializeSearchParams,
  getDefaultTimeRange,
  type InvestigationSearchState,
} from './searchSchema.js';

export function useSearchState() {
  const [searchParams, setSearchParams] = useSearchParams();

  const state = useMemo<InvestigationSearchState>(() => {
    const parsed = parseSearchParams(searchParams);

    // Apply default 24h window if neither from nor to is in URL
    if (!parsed.from && !parsed.to) {
      const def = getDefaultTimeRange();
      return {
        ...parsed,
        from: def.from,
        to: def.to,
        sort: parsed.sort ?? 'time',
        view: parsed.view ?? 'table',
        plate_match: parsed.plate_match ?? 'lookalike',
      };
    }

    return {
      ...parsed,
      sort: parsed.sort ?? 'time',
      view: parsed.view ?? 'table',
      plate_match: parsed.plate_match ?? 'lookalike',
    };
  }, [searchParams]);

  const setSearchState = useCallback(
    (nextState: InvestigationSearchState, opts: { replace?: boolean } = {}) => {
      const params = serializeSearchParams(nextState);
      setSearchParams(params, { replace: opts.replace ?? false });
    },
    [setSearchParams]
  );

  const patchSearchState = useCallback(
    (patch: Partial<InvestigationSearchState>, opts: { replace?: boolean } = {}) => {
      const next = { ...state, ...patch };
      // Delete undefined/empty keys in patch
      for (const [k, v] of Object.entries(patch)) {
        if (v === undefined || v === null || v === '') {
          delete (next as any)[k];
        }
      }
      setSearchState(next, opts);
    },
    [state, setSearchState]
  );

  const resetFilters = useCallback(() => {
    const def = getDefaultTimeRange();
    setSearchState({
      from: def.from,
      to: def.to,
      sort: 'time',
      view: 'table',
      plate_match: 'lookalike',
    });
  }, [setSearchState]);

  return {
    state,
    setSearchState,
    patchSearchState,
    resetFilters,
  };
}
