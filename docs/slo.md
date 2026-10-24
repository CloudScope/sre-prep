# SLO: orders-api

| | |
|---|---|
| Service | `orders-api` (lab sample service, namespace `demo`) |
| Owner | `<team-name>` |
| Status | Lab / illustrative. Targets are chosen to exercise the alerting, not from real user research. |
| Rules | [`lab/slo/orders-api-slo.rules.yaml`](../lab/slo/orders-api-slo.rules.yaml), tested by [`orders-api-slo.test.yaml`](../lab/slo/orders-api-slo.test.yaml) |
| Error budget policy | [`error-budget-policy.md`](error-budget-policy.md) |

## User journey

A client fetches an order by ID: `GET /orders/{order_id}`. If it errors or is slow, the user sees a broken or slow order page.

## SLIs

Both are **ratio SLIs: good events / valid events**, measured at the service (server-side HTTP metrics from the OpenTelemetry SDK, via the collector to Prometheus).

| SLI | Good event | Valid event |
|---|---|---|
| Availability | `GET /orders/{order_id}` that did **not** return 5xx | All `GET /orders/{order_id}` requests |
| Latency | `GET /orders/{order_id}` served in **≤ 250 ms** | All `GET /orders/{order_id}` requests |

Notes:
- `/healthz` is excluded at instrumentation time, so probe traffic does not inflate the SLI.
- 4xx counts as good for availability: the service answered correctly, the client sent a bad request.
- 250 ms sits on an exact histogram bucket boundary (`le="0.25"`), so the latency SLI is an exact count, not an interpolated quantile.
- Measured server-side, so it misses failures before the request reaches the pod (DNS, ingress, network). A production version should add a load balancer or synthetic probe SLI.

### Implementation (PromQL)

```promql
# Availability error ratio over window W
(sum(rate(http_server_request_duration_seconds_count{exported_job="demo/orders-api",http_route="/orders/{order_id}",http_response_status_code=~"5.."}[W])) or vector(0))
/
sum(rate(http_server_request_duration_seconds_count{exported_job="demo/orders-api",http_route="/orders/{order_id}"}[W]))

# Latency error ratio (share of requests slower than 250 ms) over window W
1 - (
  sum(rate(http_server_request_duration_seconds_bucket{exported_job="demo/orders-api",http_route="/orders/{order_id}",le="0.25"}[W]))
  /
  sum(rate(http_server_request_duration_seconds_count{exported_job="demo/orders-api",http_route="/orders/{order_id}"}[W]))
)
```

Recorded as `slo:sli_error:ratio_rate{5m,30m,1h,6h,3d,30d}{service="orders-api", slo="availability|latency"}`.
`or vector(0)` keeps the availability series at 0 when no 5xx series exists yet, instead of returning nothing.

## SLOs

Rolling **30-day** window.

| SLO | Target | Error budget | Budget in requests (at 5 req/s ≈ 12.96M req / 30d) |
|---|---|---|---|
| Availability | 99.5% | 0.5% | ≈ 64,800 failed requests |
| Latency | 99% ≤ 250 ms | 1% | ≈ 129,600 slow requests |

Budget remaining: `slo:error_budget_remaining:ratio` (1 = untouched, 0 = spent, < 0 = SLO missed).

## Alerting

Multi-window, multi-burn-rate, per the [SRE Workbook](https://sre.google/workbook/alerting-on-slos/). Burn rate = observed error ratio / error budget. A burn rate of 1 spends exactly the budget over 30 days.

| Alert | Severity | Burn rate | Long window | Short window | Budget spent when it fires |
|---|---|---|---|---|---|
| `SLOErrorBudgetBurnPage` | page (`critical`) | 14.4× | 1h | 5m | 2% |
| `SLOErrorBudgetBurnPage` | page (`critical`) | 6× | 6h | 30m | 5% |
| `SLOErrorBudgetBurnTicket` | ticket (`warning`) | 1× | 3d | 6h | 10% |

Why this shape:
- **Long window** gives significance: a 2-minute blip doesn't page.
- **Short window** gives fast reset: the alert clears soon after the problem stops, instead of firing for another hour.
- **Slow burns become tickets, not pages.** A 2× burn is a real problem but can wait for working hours. Only budget-threatening burns wake someone up.

For the availability SLO (0.5% budget) the page fires at an error ratio above 7.2% (1h) or 3% (6h). The ticket fires above 0.5% sustained over 3 days.

Verified by `promtool test rules`:
1. Healthy traffic: no alerts, budget at 100%.
2. 10% errors for 1h: page.
3. 1% errors for 3 days: ticket, no page.
4. 10% of requests > 250 ms: latency page, availability unaffected.

## Known limitations

- Low traffic makes ratios noisy (one error in 10 requests is 10%). A real service with low traffic needs a minimum request-count guard or synthetic traffic.
- Prometheus here is single-replica with local storage. Production would use HA Prometheus with long-term storage (Thanos, Mimir, or Google Cloud Managed Service for Prometheus) so the 30-day window survives restarts.
- Targets are illustrative. In a real service, pick them from historical performance and what users notice, then revisit quarterly.

## Try it

```bash
kubectl -n demo set env deploy/orders-api ERROR_RATE=0.1         # ~20x burn: page within minutes
kubectl -n demo set env deploy/orders-api EXTRA_LATENCY_MS=300   # latency SLO burn
kubectl -n demo set env deploy/orders-api ERROR_RATE=0 EXTRA_LATENCY_MS=0
```
