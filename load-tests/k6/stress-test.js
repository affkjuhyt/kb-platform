import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

// Stress test configuration
export const options = {
  stages: [
    { duration: '5m', target: 10 },   // Warm up
    { duration: '5m', target: 50 },   // Normal load
    { duration: '5m', target: 100 },  // High load
    { duration: '5m', target: 200 },  // Very high load
    { duration: '5m', target: 300 },  // Stress test
    { duration: '5m', target: 0 },    // Recovery
  ],
  thresholds: {
    http_req_duration: ['p(99) < 10000'], // 10s max
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-api-key';
const TENANT_ID = __ENV.TENANT_ID || 'test-tenant';

const searchLatency = new Trend('search_latency');

export default function () {
  const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
    'X-Tenant-ID': TENANT_ID,
  };

  const queries = [
    'machine learning',
    'deep learning', 
    'AI',
    'data science',
    'cloud computing',
  ];

  const query = queries[Math.floor(Math.random() * queries.length)];

  const startTime = Date.now();
  const response = http.post(
    `${BASE_URL}/query/search`,
    JSON.stringify({
      query: query,
      tenant_id: TENANT_ID,
      top_k: 5,
    }),
    { headers }
  );
  const endTime = Date.now();

  searchLatency.add(endTime - startTime);

  check(response, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(Math.random() * 2);
}
