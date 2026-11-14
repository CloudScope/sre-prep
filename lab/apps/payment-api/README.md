# payment-api

A production-grade Spring Boot 3.4 service instrumented with OpenTelemetry and designed with strict Zero-Trust SRE patterns:
- **Port 8080 (`0.0.0.0`)**: Serves business traffic and authenticated synthetic monitoring. Spring Security requires authentication for **every request** (`anyRequest().authenticated()`).
- **Port 8081 (`127.0.0.1`)**: Actuator strictly bound to localhost loopback. Physically unreachable from outside the Pod.
- **Sidecar Pattern**: An OpenTelemetry Collector sidecar scrapes metrics over `http://127.0.0.1:8081/actuator/prometheus` and pushes them out via OTLP.
- **Anti-False-Green Health Guard**: Includes `MainServerHealthIndicator` which inspects port 8080's Tomcat connector, ensuring `/actuator/health` fails if port 8080 crashes.

## Endpoints

| Method | Endpoint | Port | Auth Required? | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/payment/api/v1/health` | `8080` | **Yes** (`SYNTHETIC_PROBER`) | End-to-end synthetic health check |
| `POST` | `/payment/api/v1/process` | `8080` | **Yes** (Authenticated) | Process payment transactions |
| `GET` | `/actuator/health` | `8081` | No (Loopback only) | Kubelet liveness/readiness probes |
| `GET` | `/actuator/prometheus` | `8081` | No (Loopback only) | OTel sidecar metric scraping |

## Chaos & Failure Injection (Environment Variables)

- `ERROR_RATE`: Fraction of `/payment/api/v1/process` calls returning HTTP 500 (default: `0.0`).
- `EXTRA_LATENCY_MS`: Milliseconds of artificial delay added to payment processing (default: `0`).

## Testing with Curl

### 1. Synthetic Health Check (Port 8080 - Authenticated)
```bash
# Unauthenticated call (Will be rejected with 401 Unauthorized):
curl -i http://localhost:8080/payment/api/v1/health

# Authenticated call:
curl -i -u synthetic-monitor:synthetic-secret-password-123 \
  http://localhost:8080/payment/api/v1/health
```

### 2. Payment Processing (Port 8080 - Authenticated)
```bash
curl -i -u synthetic-monitor:synthetic-secret-password-123 \
  -H "Content-Type: application/json" \
  -d '{"orderId": "ord-1001", "amount": 49.99, "currency": "USD"}' \
  http://localhost:8080/payment/api/v1/process
```

### 3. Actuator Health Check (Port 8081 - From Inside the Pod)
```bash
kubectl -n demo exec -it deploy/payment-api -c payment-api -- \
  wget -qO- http://127.0.0.1:8081/actuator/health
```
