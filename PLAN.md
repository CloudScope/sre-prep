# 14-Day SRE Interview Prep Plan

Target: Senior SRE (Platform & Reliability Engineering), `<target company>`, India.
Assumed effort: 1.5–2 hours on weekdays, 3 hours on weekends. Adjust once the interview date is known.

## Progress

### Days 1–2: Lab and GCP setup
- [x] Local kind cluster running
- [x] kube-prometheus-stack installed in `monitoring` and Grafana reachable
- [x] podinfo deployed in `demo` and `/metrics` verified
- [x] OpenTelemetry Collector installed in `monitoring`
- [x] Instrumented sample app sending traces and metrics via OTel SDK
- [ ] ~~GCP free trial or Google Cloud Skills Boost: GKE and Cloud Monitoring labs~~ (skipped for now)

### Days 3–4: Observability and SLOs (biggest gap)
- [ ] Read Google SRE Book (SLO chapter) and SRE Workbook ("Implementing SLOs")
- [x] Define 2 SLIs and 1 SLO for the sample service (2 SLOs: availability 99.5%, latency 99% ≤ 250ms)
- [x] Write error budget policy (`docs/error-budget-policy.md`)
- [x] PromQL for the SLI
- [x] Multi-window, multi-burn-rate alert rules in Prometheus (`lab/slo/`, promtool-tested)
- [x] One-page SLO doc in `docs/slo.md`

### Day 5: Incident management
- [ ] Read Google SRE Book (managing incidents, postmortems)
- [ ] Write one runbook for a lab failure in `docs/runbooks/`
- [ ] Write a blameless postmortem template in `docs/postmortem-template.md`

### Days 6–7: Behavioral stories
- [ ] Story 1: production incident you resolved
- [ ] Story 2: automation that reduced toil
- [ ] Story 3: cost optimization / FinOps result
- [ ] Story 4: pipeline or deployment improvement
- [ ] Story 5: mentoring or influencing a team
- [ ] Each story practiced aloud under 2 minutes; numbers filled in with real data

### Days 8–9: Kubernetes, GKE, Terraform drills
- [ ] Troubleshooting drills: CrashLoopBackOff, OOMKilled, Pending, failing readiness probe, failed rollout
- [ ] Compare GKE Autopilot with EKS; map Workload Identity to IRSA
- [ ] Terraform: remote state, locking, drift detection, module design
- [ ] Argo CD: sync, self-heal, rollback

### Days 10–11: Python coding
- [ ] Log parsing and error-rate aggregation
- [ ] Retry with exponential backoff and jitter
- [ ] Kubernetes API call with error handling
- [ ] 15–20 problems total, timed

### Day 12: AIOps, agentic SRE, system design
- [ ] One-page POV on agentic SRE (where it helps, where human approval is required) in `docs/agentic-sre-pov.md`
- [ ] Timed design answer (15 min): 200 microservices on GKE, 99.95% SLO, avoid unnecessary night pages

### Day 13: Mock interview
- [ ] Full 60-minute loop: behavioral, troubleshooting, coding, design
- [ ] Notes on weak spots in `docs/mock-notes.md`

### Day 14: Review
- [ ] Revisit weak spots
- [ ] Re-read STAR stories and resume claims that need defending
- [ ] Check logistics: format, tools, time zone

## Resources

- Google SRE Book and SRE Workbook: https://sre.google
- OpenTelemetry docs: https://opentelemetry.io
- Prometheus docs: https://prometheus.io/docs
- Google Cloud Skills Boost: https://www.cloudskillsboost.google
- Argo CD and Terraform docs
