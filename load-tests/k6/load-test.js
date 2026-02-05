import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Custom metrics
const searchLatency = new Trend('search_latency');
const ragLatency = new Trend('rag_latency');
const extractionLatency = new Trend('extraction_latency');
const errorRate = new Rate('errors');
const httpReqFailed = new Rate('http_req_failed');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 10 },    // Ramp up to 10 users
    { duration: '5m', target: 10 },    // Stay at 10 users
    { duration: '2m', target: 20 },    // Ramp up to 20 users
    { duration: '5m', target: 20 },    // Stay at 20 users
    { duration: '2m', target: 0 },     // Ramp down
  ],
  thresholds: {
    // p95 latency should be below 2.1s (DONE criteria)
    'search_latency': ['p(95) < 2100'],
    'rag_latency': ['p(95) < 2100'],
    'http_req_duration': ['p(95) < 2100'],
    
    // Error rate should be below 1%
    'errors': ['rate < 0.01'],
    'http_req_failed': ['rate < 0.01'],
    
    // 95% of requests should succeed
    'http_req_duration': ['p(95) < 2100'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-api-key';
const TENANT_ID = __ENV.TENANT_ID || 'test-tenant';

// Search queries for testing
const searchQueries = [
  'machine learning',
  'deep learning',
  'neural networks',
  'natural language processing',
  'artificial intelligence',
  'data science',
  'big data',
  'cloud computing',
  'docker',
  'kubernetes',
];

// RAG questions for testing
const ragQuestions = [
  'What is machine learning?',
  'How does deep learning work?',
  'What are neural networks?',
  'Explain natural language processing',
  'What is artificial intelligence?',
  'How does the system handle errors?',
  'What are the security policies?',
  'How to deploy the application?',
];

export default function () {
  const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
    'X-Tenant-ID': TENANT_ID,
  };

  group('Search Operations', () => {
    const query = searchQueries[randomIntBetween(0, searchQueries.length - 1)];
    
    const startTime = new Date();
    const response = http.post(
      `${BASE_URL}/query/search`,
      JSON.stringify({
        query: query,
        tenant_id: TENANT_ID,
        top_k: 5,
      }),
      { headers }
    );
    const endTime = new Date();
    const latency = endTime - startTime;
    
    searchLatency.add(latency);
    
    const success = check(response, {
      'search status is 200': (r) => r.status === 200,
      'search has results': (r) => {
        const body = JSON.parse(r.body);
        return body.results && body.results.length > 0;
      },
    });
    
    errorRate.add(!success);
    httpReqFailed.add(response.status !== 200);
  });

  sleep(randomIntBetween(1, 3));

  group('RAG Queries', () => {
    const question = ragQuestions[randomIntBetween(0, ragQuestions.length - 1)];
    
    const startTime = new Date();
    const response = http.post(
      `${BASE_URL}/query/rag`,
      JSON.stringify({
        query: question,
        tenant_id: TENANT_ID,
        top_k: 5,
      }),
      { headers }
    );
    const endTime = new Date();
    const latency = endTime - startTime;
    
    ragLatency.add(latency);
    
    const success = check(response, {
      'rag status is 200': (r) => r.status === 200,
      'rag has answer': (r) => {
        const body = JSON.parse(r.body);
        return body.answer && body.answer.length > 0;
      },
      'rag has citations': (r) => {
        const body = JSON.parse(r.body);
        return body.citations && body.citations.length > 0;
      },
    });
    
    errorRate.add(!success);
    httpReqFailed.add(response.status !== 200);
  });

  sleep(randomIntBetween(2, 5));
}

export function handleSummary(data) {
  console.log('\n=== Load Test Summary ===');
  console.log(`Search p95 latency: ${data.metrics.search_latency.values['p(95)']}ms`);
  console.log(`RAG p95 latency: ${data.metrics.rag_latency.values['p(95)']}ms`);
  console.log(`Error rate: ${data.metrics.errors.values.rate * 100}%`);
  console.log(`Total requests: ${data.metrics.http_reqs.values.count}`);
  console.log(`Failed requests: ${data.metrics.http_req_failed.values.rate * 100}%`);
  
  // Check if p95 target met
  const searchP95 = data.metrics.search_latency.values['p(95)'];
  const ragP95 = data.metrics.rag_latency.values['p(95)'];
  
  if (searchP95 <= 2100 && ragP95 <= 2100) {
    console.log('\n✓ SUCCESS: p95 latency target met (≤ 2.1s)');
  } else {
    console.log('\n✗ FAILED: p95 latency target not met');
    console.log(`  Target: ≤ 2100ms`);
    console.log(`  Search p95: ${searchP95}ms`);
    console.log(`  RAG p95: ${ragP95}ms`);
  }
  
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'results.json': JSON.stringify(data),
  };
}
