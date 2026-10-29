import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useSearchState } from './useSearchState.js';
import { Omnibox } from './Omnibox.js';
import { FilterPanel, type FacetsData } from './FilterPanel.js';
import { ResultsTable, type EventItem } from './ResultsTable.js';
import { TimelineView } from './TimelineView.js';
import { EventDrawer } from './EventDrawer.js';
import { JourneyStrip } from './JourneyStrip.js';
import { ExportDialog } from './ExportDialog.js';
import { formatQueryTokens } from './queryParser.js';
import { serializeSearchParams } from './searchSchema.js';

export const InvestigationPage: React.FC = () => {
  const { state, setSearchState, patchSearchState, resetFilters } = useSearchState();

  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [facets, setFacets] = useState<FacetsData | null>(null);
  const [loadingFacets, setLoadingFacets] = useState(false);

  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const [selectedEvent, setSelectedEvent] = useState<EventItem | null>(null);
  const [journeyPlate, setJourneyPlate] = useState<string | null>(state.plate ?? null);
  const [exportOpen, setExportOpen] = useState(false);

  const userRole = 'INVESTIGATOR'; // Auth seam default

  // Sync journeyPlate when state.plate changes
  useEffect(() => {
    if (state.plate) {
      setJourneyPlate(state.plate);
    }
  }, [state.plate]);

  // Load events when search state changes (aborting previous in-flight request)
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    const params = serializeSearchParams(state);
    params.set('limit', '50');

    fetch(`/api/events?${params.toString()}`, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) {
          const json = await res.json().catch(() => ({}));
          throw { message: json.error?.message || `HTTP ${res.status}`, requestId: json.error?.request_id };
        }
        return res.json();
      })
      .then((json) => {
        setEvents(json.data || []);
        setNextCursor(json.meta?.next_cursor ?? null);
        setHasMore(Boolean(json.meta?.has_more));
        setLoading(false);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err);
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [state]);

  // Load facets independently
  useEffect(() => {
    const controller = new AbortController();
    setLoadingFacets(true);

    const params = serializeSearchParams(state);

    fetch(`/api/investigation/facets?${params.toString()}`, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) return null;
        return res.json();
      })
      .then((json) => {
        if (json?.data) {
          setFacets(json.data);
        }
        setLoadingFacets(false);
      })
      .catch(() => {
        setLoadingFacets(false);
      });

    return () => controller.abort();
  }, [state]);

  const loadMoreEvents = useCallback(async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);

    const params = serializeSearchParams(state);
    params.set('limit', '50');
    params.set('cursor', nextCursor);

    try {
      const res = await fetch(`/api/events?${params.toString()}`);
      if (res.ok) {
        const json = await res.json();
        setEvents((prev) => [...prev, ...(json.data || [])]);
        setNextCursor(json.meta?.next_cursor ?? null);
        setHasMore(Boolean(json.meta?.has_more));
      }
    } finally {
      setLoadingMore(false);
    }
  }, [nextCursor, loadingMore, state]);

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans select-none">
      {/* Top Navigation Bar */}
      <header className="h-14 border-b border-slate-800 bg-slate-900 px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-100 bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 rounded-lg border border-slate-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Live Monitor
          </Link>
          <div className="h-4 w-px bg-slate-800" />
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-sky-950 text-sky-400 border border-sky-800/60">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
            <h1 className="text-sm font-bold tracking-wide uppercase text-slate-100">
              Forensic Investigation Workbench
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-950 rounded-lg p-0.5 border border-slate-800">
            <button
              type="button"
              onClick={() => patchSearchState({ view: 'table' })}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                (state.view ?? 'table') === 'table'
                  ? 'bg-slate-800 text-sky-400 shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Table View
            </button>
            <button
              type="button"
              onClick={() => patchSearchState({ view: 'timeline' })}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                state.view === 'timeline'
                  ? 'bg-slate-800 text-sky-400 shadow-xs'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Timeline View
            </button>
          </div>

          <button
            type="button"
            onClick={() => setExportOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export CSV
          </button>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Filter Panel */}
        <aside className="w-80 border-r border-slate-800 p-4 overflow-y-auto shrink-0 bg-slate-950/40">
          <FilterPanel
            state={state}
            facets={facets}
            loadingFacets={loadingFacets}
            onPatchState={patchSearchState}
            onReset={resetFilters}
            userRole={userRole}
          />
        </aside>

        {/* Center Results Pane */}
        <main className="flex-1 flex flex-col p-4 overflow-hidden gap-4 min-w-0">
          {/* Omnibox Search Bar */}
          <div className="shrink-0">
            <Omnibox
              initialValue={formatQueryTokens(state)}
              onSearch={(parsed) => {
                setSearchState({
                  ...state,
                  ...parsed.state,
                });
              }}
            />
          </div>

          {/* Active Vehicle Journey Strip */}
          {journeyPlate && (
            <div className="shrink-0">
              <JourneyStrip
                plate={journeyPlate}
                onClose={() => setJourneyPlate(null)}
                onSelectSighting={(camId, from, to) => {
                  patchSearchState({
                    camera_id: [camId],
                    from,
                    to,
                  });
                }}
              />
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-3 bg-red-950/50 border border-red-800/60 rounded-lg text-xs text-red-200 flex items-center justify-between">
              <span>{error.message}</span>
              {error.requestId && (
                <span className="font-mono text-[10px] text-red-400">Request ID: {error.requestId}</span>
              )}
            </div>
          )}

          {/* Results Area */}
          <div className="flex-1 overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center h-full text-slate-400 text-sm">
                <div className="w-5 h-5 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mr-3" />
                Searching events...
              </div>
            ) : state.view === 'timeline' ? (
              <TimelineView
                events={events}
                fromTime={state.from}
                toTime={state.to}
                selectedEventId={selectedEvent?.event_id}
                onSelectEvent={(ev) => setSelectedEvent(ev)}
                onTimeRangeChange={(from, to) => patchSearchState({ from, to })}
              />
            ) : (
              <ResultsTable
                events={events}
                selectedEventId={selectedEvent?.event_id}
                onSelectEvent={(ev) => setSelectedEvent(ev)}
                onInvestigateJourney={(p) => setJourneyPlate(p)}
                hasMore={hasMore}
                loadingMore={loadingMore}
                onLoadMore={loadMoreEvents}
              />
            )}
          </div>
        </main>

        {/* Right Event Detail Drawer */}
        <EventDrawer
          eventId={selectedEvent?.event_id ?? null}
          onClose={() => setSelectedEvent(null)}
          onSelectEventId={(id) => {
            const found = events.find((e) => e.event_id === id);
            if (found) setSelectedEvent(found);
          }}
          onFilterCamera={(cam) => patchSearchState({ camera_id: [cam] })}
          onFilterPlate={(p) => {
            patchSearchState({ plate: p });
            setJourneyPlate(p);
          }}
          onViewJourney={(p) => setJourneyPlate(p)}
        />
      </div>

      {/* Export Dialog Modal */}
      <ExportDialog
        isOpen={exportOpen}
        onClose={() => setExportOpen(false)}
        state={state}
      />
    </div>
  );
};
