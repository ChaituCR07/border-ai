import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useUIStore } from '../../state/uiStore';
import type { AlertResource } from '../../api/types';

export interface AlertDetailData extends AlertResource {
  notifications?: {
    total: number;
    sent: number;
    pending: number;
    failed: number;
    cancelled: number;
  };
  explanation?: Record<string, unknown> | null;
}

export function useAlertDeepLink(onAlertLoaded?: (alert: AlertDetailData) => void) {
  const [searchParams, setSearchParams] = useSearchParams();
  const alertId = searchParams.get('alert');
  const setSelectedCamera = useUIStore((s) => s.setSelectedCamera);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [alert, setAlert] = useState<AlertDetailData | null>(null);

  useEffect(() => {
    if (!alertId) {
      setAlert(null);
      setError(null);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    fetch(`/api/alerts/${encodeURIComponent(alertId)}`, {
      headers: {
        Accept: 'application/json',
      },
    })
      .then(async (res) => {
        if (!active) return;
        if (res.status === 404) {
          setError(`Alert not found or retention period expired.`);
          setAlert(null);
          return;
        }
        if (!res.ok) {
          setError(`Failed to load alert details (${res.status} ${res.statusText}).`);
          setAlert(null);
          return;
        }
        const json = await res.json();
        const alertData: AlertDetailData = json.data;
        setAlert(alertData);
        if (alertData.event?.camera_id) {
          setSelectedCamera(alertData.event.camera_id);
        }
        onAlertLoaded?.(alertData);
      })
      .catch((err) => {
        if (!active) return;
        setError(`Network error loading alert: ${err.message || 'unknown error'}`);
        setAlert(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [alertId, setSelectedCamera, onAlertLoaded]);

  const clearAlertParam = useCallback(() => {
    const next = new URLSearchParams(searchParams);
    next.delete('alert');
    setSearchParams(next, { replace: true });
    setAlert(null);
    setError(null);
  }, [searchParams, setSearchParams]);

  return {
    alertId,
    alert,
    loading,
    error,
    clearAlertParam,
  };
}
