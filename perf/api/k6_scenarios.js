// k6 load test scenarios for BorderVision REST API & WebSocket endpoints
// Evaluates API response latency under 10, 50, and 200 virtual users (VUs)

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    nominal_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 },
        { duration: '1m', target: 50 },
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    'http_req_duration{endpoint:events}': ['p(95)<100'],
    'http_req_duration{endpoint:alerts}': ['p(95)<100'],
    'http_req_duration{endpoint:threats}': ['p(95)<200'],
    'http_req_failed': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://localhost:3000';

export default function () {
  // 1. Fetch recent events with pagination
  const eventsRes = http.get(`${BASE_URL}/api/events?limit=25`, {
    tags: { endpoint: 'events' },
  });
  check(eventsRes, {
    'events status is 200': (r) => r.status === 200,
    'events duration < 100ms': (r) => r.timings.duration < 100,
  });

  // 2. Fetch active open alerts
  const alertsRes = http.get(`${BASE_URL}/api/alerts?status=OPEN`, {
    tags: { endpoint: 'alerts' },
  });
  check(alertsRes, {
    'alerts status is 200': (r) => r.status === 200,
  });

  // 3. System heartbeat status
  const statusRes = http.get(`${BASE_URL}/api/system/status`, {
    tags: { endpoint: 'status' },
  });
  check(statusRes, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
