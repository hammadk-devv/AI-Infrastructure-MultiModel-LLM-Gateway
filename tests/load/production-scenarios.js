import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    constant_load: {
      executor: 'constant-arrival-rate',
      rate: 100, // 100 requests per second
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
    spike_test: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      stages: [
        { target: 500, duration: '1m' },
        { target: 500, duration: '2m' },
        { target: 0, duration: '1m' },
      ],
      startTime: '5m',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const API_KEY = 'lkg_test_123';
const BASE_URL = 'http://localhost:8000';

export default function () {
  const url = `${BASE_URL}/v1/chat/completions`;
  const payload = JSON.stringify({
    model: 'gpt-4o',
    messages: [{ role: 'user', content: 'Load test ping' }],
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
  };

  const res = http.post(url, payload, params);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'latency is low': (r) => r.timings.duration < 1000,
  });

  sleep(0.1);
}
