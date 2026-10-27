import type { AlertView, ServerMessage } from '@border-ai/protocol';

export type AlertMessage = Extract<ServerMessage, { type: 'alert.created' | 'alert.updated' }>;

/**
 * Pure, idempotent reducer for live alert state deltas (Task 7).
 * Replaying the same message twice produces an identical list.
 */
export function applyAlertMessage(
  list: AlertView[],
  message: AlertMessage
): AlertView[] {
  const alert = message.data.alert;
  const without = list.filter((item) => item.alert_id !== alert.alert_id);

  // If status is ACKNOWLEDGED or RESOLVED, remove from the open alert list
  if (alert.status !== 'OPEN') {
    return without;
  }

  // Prepend/upsert into the open list (sorting is handled in selector/useOpenAlerts)
  return [alert, ...without];
}
