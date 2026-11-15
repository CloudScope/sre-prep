# LiteLLM AI Gateway on Kubernetes (Stateful GitOps)

A production-grade, stateful deployment of **LiteLLM Proxy & Admin Dashboard** managed by **Argo CD** using the official OCI Helm chart backed by a dedicated **PostgreSQL 16** database.

- **Stateful Architecture**: Backed by a dedicated PostgreSQL StatefulSet (`postgres:16-alpine`) with PVC persistence.
- **Admin UI & Key Management**: Full LiteLLM Dashboard at `/ui` for managing virtual keys, per-team budgets, rate limits, and viewing spend analytics.
- **Automated Schema Migrations**: Managed via Argo CD `PreSync` job running Prisma migrations automatically on each rollout.
- **GitOps Managed**: Deployed via Argo CD multi-source Application in [litellm.yaml](file:///Users/raghunath/Documents/github/sre-prep/lab/argocd/apps/litellm.yaml) and [litellm-postgres.yaml](file:///Users/raghunath/Documents/github/sre-prep/lab/argocd/apps/litellm-postgres.yaml).
- **Distributed Tracing**: Exports OTLP traces directly to the in-cluster OpenTelemetry Collector gateway (`jaeger`).

---

## Architecture

```
+---------------------------------------------------------------------------------------+
| Argo CD App-of-Apps (root.yaml)                                                       |
|   ├── Wave 1: litellm-postgres (StatefulSet + Secret + Service)                       |
|   └── Wave 2: litellm (OCI Helm Chart 1.109.1 + PreSync Prisma Migrations)           |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v Deploys into namespace: litellm
+---------------------------------------------------------------------------------------+
| Namespace: litellm                                                                    |
|                                                                                       |
|   +------------------------------------+       read/write       +-------------------+ |
|   | LiteLLM Proxy & UI (:4000)         | ---------------------> | PostgreSQL (:5432)| |
|   | - Master Key Auth                  |                        | - 1Gi PVC (Local) | |
|   | - Models: mock-model, gpt-4o, ...  |                        | - DB: litellm     | |
|   +------------------------------------+                        +-------------------+ |
|                     |                                                     ^           |
|                     | runs on sync                                        |           |
|                     v                                                     |           |
|   +------------------------------------+                                  |           |
|   | Prisma Migrations (K8s Job)        | ---------------------------------+           |
|   | - Creates LiteLLM schema & tables  |                                              |
|   +------------------------------------+                                              |
+---------------------------------------------------------------------------------------+
```

---

## Accessing the LiteLLM Admin UI

1. **Port-Forward LiteLLM**:
   ```bash
   kubectl -n litellm port-forward svc/litellm 4000:4000
   ```

2. **Open in Browser**:
   Navigate to:
   ```
   http://localhost:4000/ui
   ```

3. **Login with Master Key**:
   ```text
   sk-litellm-master-key-lab
   ```

Inside the UI, you can:
- Generate Virtual API Keys with custom budgets (e.g. \$10/month), rate limits (RPM/TPM), and allowed models.
- Inspect real-time spend logs and request latencies.
- Test models directly in the interactive playground.

---

## Quick Testing Guide

### 1. Check Health Endpoints
```bash
curl -i http://localhost:4000/health/liveliness
curl -i http://localhost:4000/health/readiness
```
*Expected response: HTTP 200 `"I'm alive!"` / `{"status": "healthy"}`*

### 2. Generate a Virtual API Key (CLI)
You can generate virtual API keys via the proxy API:
```bash
curl -s http://localhost:4000/key/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-litellm-master-key-lab" \
  -d '{
    "key_alias": "sre-team-key",
    "models": ["mock-model", "gpt-4o"],
    "max_budget": 50.0
  }' | jq .
```

### 3. Test Chat Completion with Virtual Key
```bash
curl -s http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <GENERATED_KEY>" \
  -d '{
    "model": "mock-model",
    "messages": [{"role": "user", "content": "Hello LiteLLM with DB persistence!"}]
  }' | jq .
```

### 4. Query PostgreSQL Directly
Check persisted keys and spend records in PostgreSQL:
```bash
kubectl exec -n litellm litellm-postgresql-0 -- psql -U litellm -d litellm -c "SELECT key_alias, key_name, max_budget, spend FROM \"LiteLLM_VerificationToken\";"
kubectl exec -n litellm litellm-postgresql-0 -- psql -U litellm -d litellm -c "SELECT count(*) FROM \"LiteLLM_SpendLogs\";"
```

---

## Adding Real Provider API Keys (Optional)

To enable live routing for `gpt-4o` and `gemini-1.5-pro`, update the environment variables or inject a secret:
```bash
kubectl -n litellm create secret generic litellm-secrets \
  --from-literal=OPENAI_API_KEY="sk-..." \
  --from-literal=GEMINI_API_KEY="AIza..."
```
Then reference `litellm-secrets` in [litellm-values.yaml](file:///Users/raghunath/Documents/github/sre-prep/lab/helm/litellm-values.yaml).
