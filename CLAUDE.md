# CLAUDE.md — Context for this repo

This repo is a 14-day interview preparation project for a **Senior SRE role** (Platform & Reliability Engineering, `<target company>`, India, hybrid). The candidate is a Sr. DevOps engineer with 9+ years of experience (AWS, EKS, Terraform, Argo CD, Jenkins/GitHub Actions, Grafana, New Relic, Prometheus, Splunk, Python/Shell).

## Goals

1. Close the candidate's gaps against the JD:
   - SLOs, SLIs, error budgets, burn-rate alerting (core gap)
   - OpenTelemetry (not on resume yet)
   - GCP / GKE / Cloud Monitoring (resume is AWS and Azure only)
   - Incident management: incident command, postmortems, on-call
   - Service mesh and API gateways (nice to have)
   - Mentoring and technical leadership
2. Produce a portfolio-quality lab in `lab/` that demonstrates observability and SLO work on a local kind cluster.
3. Prepare 5 STAR stories, a timed system design answer, and Python coding practice.
4. Run at least one full mock interview.

## How to help in this repo

- Be direct and practical. The candidate wants checklists, commands they can run, and feedback they can act on.
- When writing lab config (Helm values, Prometheus rules, OTel Collector config), prefer tested, minimal examples and say which chart and version they target. Don't invent chart values; check docs if unsure.
- Don't put real company names, internal details, or credentials in files. Use placeholders.
- Keep every claim the candidate might make in an interview defensible: SLO docs and STAR stories should use placeholders for numbers until the candidate supplies real figures.
- Track progress in `PLAN.md` by ticking the checkboxes as tasks finish.

## Environment

- Local kind cluster (`kind`), Helm, kubectl.
- Lab namespaces: `monitoring` (kube-prometheus-stack, OTel Collector), `demo` (sample app).
- Sample app for Day 1: podinfo (Helm chart from https://stefanprodan.github.io/podinfo).
- Day 2 onward: a small instrumented app using the OpenTelemetry SDK.
