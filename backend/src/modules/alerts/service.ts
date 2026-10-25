import type { AlertsRepo, AlertFilters } from './repo.js';
import type { AlertResource, Actor } from '../../types/domain.js';
import type { AuditRepo } from '../../common/audit.js';
import { clampLimit, decodeCursor, encodeCursor, type Cursor, type PaginatedResponse } from '../../common/pagination.js';
import { notFound } from '../../common/errors.js';
import { validateTimeRange } from '../../common/time.js';

export type AlertChangeCallback = (alert: AlertResource) => void;

export class AlertsService {
  constructor(
    private readonly repo: AlertsRepo,
    private readonly audit?: AuditRepo,
    private readonly onAlertChanged?: AlertChangeCallback
  ) {}

  async list(query: any): Promise<PaginatedResponse<AlertResource>> {
    validateTimeRange(query.from, query.to);

    const limit = clampLimit(query.limit, 50, 200);
    const cursor: Cursor | undefined = query.cursor ? decodeCursor(query.cursor) : undefined;

    const filters: AlertFilters = {
      status: query.status,
      priority: query.priority,
      cameraId: query.camera_id,
      from: query.from,
      to: query.to,
    };

    const rows = await this.repo.list(filters, limit + 1, cursor);
    const hasMore = rows.length > limit;
    const pageRows = hasMore ? rows.slice(0, limit) : rows;

    const nextCursor = hasMore && pageRows.length > 0
      ? encodeCursor({
          t: pageRows[pageRows.length - 1]!.created_at,
          id: pageRows[pageRows.length - 1]!.alert_id,
        })
      : null;

    return {
      data: pageRows,
      meta: {
        limit,
        next_cursor: nextCursor,
        has_more: hasMore,
      },
    };
  }

  async acknowledge(
    id: string,
    acknowledgedBy: string | undefined,
    actor: Actor,
    requestId?: string
  ): Promise<AlertResource> {
    const operator = acknowledgedBy || actor.id;
    const result = await this.repo.acknowledge(id, operator);
    if (!result) {
      throw notFound(`Alert '${id}'`);
    }

    // Audit and notify only on actual transition
    if (result.updated) {
      if (this.audit) {
        await this.audit.record({
          actor: operator,
          action: 'ALERT_ACK',
          entity_type: 'ALERT',
          entity_id: id,
          request_id: requestId,
          detail: { priority: result.alert.priority, event_id: result.alert.event_id },
        });
      }

      if (this.onAlertChanged) {
        this.onAlertChanged(result.alert);
      }
    }

    return result.alert;
  }
}
