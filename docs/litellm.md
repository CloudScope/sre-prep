# LiteLLM AI Gateway on Kubernetes (Stateless GitOps)

A production-grade, stateless deployment of **LiteLLM Proxy** managed by **Argo CD** using the official OCI Helm chart:
- **Stateless Architecture**: Zero database dependencies; configuration, routing rules, and mock models are mounted via a GitOps-managed `ConfigMap`.
- **GitOps Managed**: Deployed via Argo CD multi-source Application in `lab/argocd/apps/litellm.yaml`.
- **Prometheus Metrics**: Exports token usage, latency, and request counts via `/metrics`, automatically scraped by Prometheus Operator (`ServiceMonitor`).
- **Distributed Tracing**: Exports OTLP traces directly to the in-cluster OpenTelemetry Collector gateway (`jaeger`).

---

## Architecture

```
+---------------------------------------------------------------------------------------+
| Argo CD App-of-Apps (root.yaml)                                                       |
|   Pulls oci://ghcr.io/berriai/litellm-helm + Git values (litellm-values.yaml)        |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v Deploys into namespace: litellm
+---------------------------------------------------------------------------------------+
| Pod: litellm                                                                          |
|   - Image: ghcr.io/berriai/litellm:main-v1.61.1                                       |
|   - Port 4000: OpenAI-compatible API & Prometheus /metrics                            |
|   - Models: mock-model, gpt-4o, gemini-1.5-pro                                        |
+-------------------------------------------+-------------------------------------------+
                                            |
                               +------------+------------+
                               |                         |
                               v Scrapes :4000/metrics   v Pushes OTLP Traces
                     [Prometheus Operator]       [OTel Collector -> Jaeger]
```

---

## Quick Testing Guide

### 1. Port-Forward LiteLLM to Your Laptop
```bash
kubectl -n litellm port-forward svc/litellm 4000:4000
```

### 2. Test Health Endpoint
```bash
curl -i http://localhost:4000/health/liveliness
curl -i http://localhost:4000/health/readiness
```
*Expected response: HTTP 200 `"I'm alive!"` / `{"status": "healthy"}`*

### 3. Test Zero-Cost Mock Model
You can test the entire AI gateway pipeline without providing real API keys:
```bash
curl -i http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-litellm-master-key-lab" \
  -d '{
    "model": "mock-model",
    "messages": [{"role": "user", "content": "Hello LiteLLM!"}]
  }'
```
*Expected response: Instant OpenAI-compatible response with mock completion.*

### 4. Check Prometheus Metrics
LiteLLM exposes standard Prometheus metrics at `/metrics`:
```bash
curl http://localhost:4000/metrics | grep litellm
```
Key metrics:
- `litellm_requests_metric_total`: Total request counter by model and API key.
- `litellm_spend_metric_total`: Cumulative cost spend by model.
- `litellm_latency_metric_seconds`: Request duration histogram.

---

## Adding Real Provider API Keys (Optional)

To enable real model routing (`gpt-4o`, `gemini-1.5-pro`), create a Kubernetes secret in the `litellm` namespace:

```bash
kubectl -n litellm create secret generic litellm-secrets \
  --from-literal=OPENAI_API_KEY="sk-..." \
  --from-literal=GEMINI_API_KEY="AIza..."
```
Then reference `litellm-secrets` in `lab/helm/litellm-values.yaml`:
```yaml
environmentSecrets:
  - litellm-secrets
```
