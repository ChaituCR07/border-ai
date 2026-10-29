import type { FastifyInstance, FastifyPluginAsync } from 'fastify';
import type { ZodTypeProvider } from 'fastify-type-provider-zod';
import { z } from 'zod';
import { InvestigationService } from './service.js';
import type { InvestigationRepo } from './repo.js';
import type { EventsRepo, EventFilters } from '../events/repo.js';
import type { AuditRepo } from '../../common/audit.js';
import { AppError } from '../../common/errors.js';
import { csvCell } from '../../common/csv.js';
import { classifyOmniboxQuery } from './query-classifier.js';
import {
  FacetsQuerySchema,
  FacetsResponseSchema,
  SuggestQuerySchema,
  SuggestResponseSchema,
  JourneyQuerySchema,
  JourneyResponseSchema,
  ExportQuerySchema,
} from './schemas.js';

export interface InvestigationRouteDeps {
  investigationRepo: InvestigationRepo;
  eventsRepo?: EventsRepo;
  auditRepo?: AuditRepo;
}

export function investigationRoutes(deps: InvestigationRouteDeps): FastifyPluginAsync {
  const service = new InvestigationService(deps.investigationRepo);

  return async (fastify: FastifyInstance) => {
    const app = fastify.withTypeProvider<ZodTypeProvider>();

    app.get(
      '/investigation/facets',
      {
        schema: {
          tags: ['Investigation'],
          summary: 'Get disjunctive facet counts for investigation filters',
          querystring: FacetsQuerySchema,
          response: {
            200: FacetsResponseSchema,
          },
        },
      },
      async (req) => {
        return service.getFacets(req.query);
      }
    );

    app.get(
      '/investigation/suggest',
      {
        schema: {
          tags: ['Investigation'],
          summary: 'Typeahead suggestion for plates, cameras, and person identifiers',
          querystring: SuggestQuerySchema,
          response: {
            200: SuggestResponseSchema,
          },
        },
      },
      async (req) => {
        return service.suggest(req.query.kind, req.query.prefix, req.actor?.role);
      }
    );

    app.get(
      '/investigation/journey',
      {
        schema: {
          tags: ['Investigation'],
          summary: 'Get vehicle journey (chronological sightings and transitions)',
          querystring: JourneyQuerySchema,
          response: {
            200: JourneyResponseSchema,
          },
        },
      },
      async (req) => {
        const result = await service.getJourney(req.query);

        deps.auditRepo?.record({
          actor: req.actor?.id ?? 'anonymous',
          action: 'JOURNEY',
          entity_type: req.query.vehicle_id ? 'vehicle' : 'plate',
          entity_id: req.query.vehicle_id ?? req.query.plate ?? '',
          request_id: req.id,
          detail: {
            actor_role: req.actor?.role,
            endpoint: '/api/investigation/journey',
            query_json: req.query,
            row_count: result.data.total_events,
            ip: req.ip,
          },
        }).catch(() => {});

        return result;
      }
    );

    app.get(
      '/investigation/export.csv',
      {
        schema: {
          tags: ['Investigation'],
          summary: 'Stream filtered events as CSV with formula injection protection',
          querystring: ExportQuerySchema,
        },
      },
      async (req, reply) => {
        const role = req.actor?.role;
        if (role !== 'INVESTIGATOR' && role !== 'ADMIN') {
          throw new AppError(403, 'FORBIDDEN', 'Export is restricted to investigators and administrators');
        }

        const query = req.query;
        if (!query.purpose || query.purpose.trim().length < 5) {
          throw new AppError(422, 'PURPOSE_REQUIRED', 'Export requires an explicit purpose (>= 5 characters)');
        }

        let omniboxParsed: Record<string, string> = {};
        if (query.q) {
          omniboxParsed = classifyOmniboxQuery(query.q);
        }

        const cameraId = query.camera_id ?? omniboxParsed.cameraId;
        const cameraIds = cameraId
          ? cameraId.split(',').map((s: string) => s.trim()).filter(Boolean)
          : undefined;

        const eventType = query.event_type ?? omniboxParsed.eventType;
        const eventTypes = eventType
          ? eventType.split(',').map((s: string) => s.trim()).filter(Boolean)
          : undefined;

        const severities = query.severity
          ? query.severity.split(',').map((s: string) => s.trim() as any).filter(Boolean)
          : undefined;

        const plate = query.plate ?? omniboxParsed.plate;
        const plateMatch = query.plate_match ?? (omniboxParsed.plateMatch as any) ?? 'lookalike';

        const filters: EventFilters = {
          eventId: omniboxParsed.eventId,
          cameraId: cameraIds && cameraIds.length === 1 ? cameraIds[0] : undefined,
          cameraIds: cameraIds && cameraIds.length > 1 ? cameraIds : undefined,
          eventTypes,
          severities,
          minScore: query.min_score,
          maxScore: query.max_score,
          from: query.from,
          to: query.to,
          trackId: query.track_id,
          plate,
          plateMatch,
          vehicleId: query.vehicle_id,
          personId: query.person_id,
          timeFrom: query.time_from,
          timeTo: query.time_to,
          tz: query.tz,
          sort: 'time',
        };

        const rows = deps.eventsRepo ? await deps.eventsRepo.list(filters, 10001) : [];

        const isTruncated = rows.length > 10000;
        const exportRows = isTruncated ? rows.slice(0, 10000) : rows;

        // Audit log export
        deps.auditRepo?.record({
          actor: req.actor?.id ?? 'anonymous',
          action: 'EXPORT',
          entity_type: 'events',
          entity_id: 'export.csv',
          request_id: req.id,
          detail: {
            actor_role: req.actor?.role,
            endpoint: '/api/investigation/export.csv',
            query_json: query,
            purpose: query.purpose,
            row_count: exportRows.length,
            truncated: isTruncated,
            ip: req.ip,
          },
        }).catch(() => {});

        const dateStr = new Date().toISOString().replace(/[-:]/g, '').replace('T', '-').split('.')[0];
        reply.header('Content-Type', 'text/csv; charset=utf-8');
        reply.header('Content-Disposition', `attachment; filename="events-${dateStr}.csv"`);

        const headers = [
          'timestamp',
          'camera_id',
          'event_type',
          'threat_score',
          'severity',
          'plate',
          'vehicle_id',
          'person_id',
          'snapshot_url',
          'explanation_summary',
        ];

        let csv = headers.join(',') + '\r\n';

        for (const r of exportRows) {
          const snapshotUrl = r.snapshot_path ? `/api/snapshots/${r.snapshot_path.replace(/^\/+/, '')}` : '';
          const expl = r.metadata?.explanation as any;
          const factors = expl?.factors ? expl.factors.map((f: any) => `${f.name}:${f.points}`).join('; ') : '';

          const cells = [
            csvCell(r.timestamp),
            csvCell(r.camera_id),
            csvCell(r.event_type),
            csvCell(r.threat_score),
            csvCell(r.severity),
            csvCell(r.plate),
            csvCell(r.vehicle_id),
            csvCell(r.person_id),
            csvCell(snapshotUrl),
            csvCell(factors),
          ];
          csv += cells.join(',') + '\r\n';
        }

        if (isTruncated) {
          csv += '# TRUNCATED: Export capped at 10000 rows. Narrow your filters.\r\n';
        }

        return reply.send(csv);
      }
    );
  };
}
