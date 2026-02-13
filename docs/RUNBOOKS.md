# Production Runbooks: AI Infrastructure LLM Gateway

## 🚨 Incident Response

### 1. Provider Outage (e.g., OpenAI/Anthropic down)
**Symptoms:** 503/429 errors from provider, increased failure logs.
**Action:**
- The Gateway automatically attempts fallbacks based on `priority` in the `ModelRegistry`.
- Verify fallback status: `SELECT * FROM audit_logs WHERE event_type='fallback_triggered';`
- If all fallbacks fail, route traffic to a secondary provider manually by boosting its priority in the Admin API.

### 2. Database Performance Degradation
**Symptoms:** High latency on model resolution (>10ms), connection exhaustion.
**Action:**
- Check RDS Proxy metrics.
- Boost instance class of Aurora replicas.
- Verify `gateway.db` (if in portable mode) or Aurora connections.

### 3. Redis Failure
**Symptoms:** 500 errors on authentication, rate limits not being enforced.
**Action:**
- Restart ElastiCache nodes.
- If persistent, bypass rate limiting by setting `rate_limit_enabled: false` in settings (requires app restart).

## 🚀 Deployment Procedures

### Zero-Downtime Migration
1. Run `./scripts/deploy.sh <tag>`
2. Monitor ALB target group health.
3. Verify metrics in Prometheus/Grafana.

## 📈 Scaling Events
- **Horizontal Scaling:** The ECS Service is configured for auto-scaling. If traffic spikes, Fargate will spin up new tasks once CPU > 70%.
- **Vertical Scaling:** Adjust `cpu` and `memory` in `task_definition.app` and run a new deployment.
