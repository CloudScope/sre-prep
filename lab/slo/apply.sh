#!/usr/bin/env bash
# Wraps the plain Prometheus rules file in a PrometheusRule CR and applies it.
# The plain file stays the source of truth so promtool can test it directly:
#   promtool test rules lab/slo/orders-api-slo.test.yaml
set -euo pipefail
cd "$(dirname "$0")"

{
  cat <<'HDR'
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: orders-api-slo
  namespace: monitoring
  labels:
    app.kubernetes.io/name: orders-api-slo
spec:
HDR
  grep -v '^#' orders-api-slo.rules.yaml | sed 's/^/  /'
} | kubectl apply -f -
