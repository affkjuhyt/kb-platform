import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Spike test configuration
export const options = {
  stages: [
    { duration: '2m', target: 10 },      // Baseline
    { duration: '30s', target: 100 },    // Spike to 100 users
    { duration: '2m', target: 100 },     // Stay at spike
    { duration: '30s', target: 10 },     // Recover
    { duration: '2m', target: 10 },      // Baseline
  ],
  thresholds: {
    'http_req_duration': ['p(95) < 5000'], // Allow higher latency during spike
    'http_req_failed': ['rate < 0.05'],    // Allow up to 5% errors during spike
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-api-key';
const TENANT_ID = __ENV.TENANT_ID || 'test-tenant';

const errorRate = new Rate('errors');

export default function () {
  const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
    'X-Tenant-ID': TENANT_ID,
  };

  // Rapid search requests
  const response = http.post(
    `${BASE_URL}/query/search`,
    JSON.stringify({
      query: 'machine learning',
      tenant_id: TENANT_ID,
      top_k: 5,
    }),
    { headers }
  );

  const success = check(response, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
    'response time < 5s': (r) => r.timings.duration < 5000,
  });

  errorRate.add(!success);

  sleep(0.1); // Very short sleep to simulate spike
}
