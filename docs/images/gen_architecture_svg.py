"""Generates docs/images/architecture.svg. Run: python3 docs/images/gen_architecture_svg.py docs/images/architecture.svg"""
import sys
from xml.sax.saxutils import escape

EDGE, INK, QUIET, TINT, BG = "#9CA3AF", "#111827", "#4B5563", "#F3F4F6", "#FFFFFF"
GIT, WORK, PIPE, STORE, UI = "#475569", "#EA580C", "#2563EB", "#059669", "#DB2777"
out = []
def add(s): out.append(s)
def text(x, y, s, size=13, weight=400, fill=INK, anchor="start"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')
def box(x, y, w, h, c, strong=False):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{c}" fill-opacity="{0.14 if strong else 0.08}" stroke="{c}" stroke-width="{2 if strong else 1.25}"/>')
def chip(x, y, w, h, c):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{BG}" fill-opacity="0.6" stroke="{c}" stroke-width="1"/>')
def zone(x, y, w, h):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{TINT}" stroke="{EDGE}" stroke-width="1"/>')
def path(d, arrow=True, dash=False):
    add(f'<path d="{d}" fill="none" stroke="{EDGE}" stroke-width="1.25"' + (' stroke-dasharray="4 3"' if dash else '') + (' marker-end="url(#arrow)"' if arrow else '') + '/>')
def badge(cx, cy, c, n):
    add(f'<circle cx="{cx}" cy="{cy}" r="10" fill="{BG}" stroke="{c}" stroke-width="1.25"/>')
    add(f'<circle cx="{cx}" cy="{cy}" r="10" fill="{c}" fill-opacity="0.25"/>')
    text(cx, cy + 4, n, 11.5, 600, INK, "middle")
def named(x, y, w, h, c, name, lines, strong=False):
    box(x, y, w, h, c, strong); cx = x + w / 2
    text(cx, y + 24, name, 13, 600, INK, "middle")
    for i, l in enumerate(lines): text(cx, y + 42 + 16 * i, l, 11.5, 400, INK if strong else QUIET, "middle")

W, H = 760, 788
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Helvetica, Arial, sans-serif" role="img" aria-label="From commit to trace: how the platform fits together">')
add(f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{EDGE}"/></marker></defs>')
add(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
text(24, 30, "From commit to trace: how the platform fits together", 15, 600)
text(24, 50, "Numbered steps follow one change and one request; colours mark the layer.", 11.5, 400, QUIET)
# GitOps band
zone(24, 68, 712, 104); text(40, 90, "GitOps", 11.5, 600, QUIET)
named(40, 100, 180, 56, GIT, "Engineer", ["commits a change"])
named(290, 100, 180, 56, GIT, "GitHub repo", ["values, manifests, rules"])
named(540, 100, 180, 56, GIT, "Argo CD", ["8 apps, self-heal on"])
# cluster
zone(24, 196, 712, 432); text(40, 220, "kind cluster, single node", 13, 600)
text(40, 246, "Workloads (ns demo)", 11.5, 600, QUIET); text(264, 246, "Pipeline (ns monitoring)", 11.5, 600, QUIET); text(516, 246, "Backends (ns monitoring)", 11.5, 600, QUIET)
named(40, 260, 184, 56, WORK, "orders-loadgen", ["about 5 req/s"])
box(40, 340, 184, 172, WORK); text(132, 364, "orders-api", 13, 600, INK, "middle"); text(132, 382, "FastAPI, OTel SDK 1.45", 11.5, 400, QUIET, "middle")
chip(56, 398, 152, 44, WORK); text(132, 416, "TracerProvider", 12, 600, INK, "middle"); text(132, 432, "batch span export", 11.5, 400, QUIET, "middle")
chip(56, 454, 152, 44, WORK); text(132, 472, "MeterProvider", 12, 600, INK, "middle"); text(132, 488, "metrics every 15 s", 11.5, 400, QUIET, "middle")
box(264, 260, 212, 270, PIPE, True); text(370, 284, "OTel Collector", 13, 600, INK, "middle"); text(370, 302, "OTLP :4317 gRPC, :4318 HTTP", 11.5, 400, INK, "middle")
chip(280, 318, 180, 44, PIPE); text(370, 336, "receivers", 12, 600, INK, "middle"); text(370, 352, "otlp", 11.5, 400, QUIET, "middle")
chip(280, 378, 180, 60, PIPE); text(370, 396, "processors", 12, 600, INK, "middle"); text(370, 412, "memory_limiter", 11.5, 400, QUIET, "middle"); text(370, 428, "k8sattributes, batch", 11.5, 400, QUIET, "middle")
chip(280, 454, 180, 60, PIPE); text(370, 472, "exporters", 12, 600, INK, "middle"); text(370, 488, "prometheus :8889", 11.5, 400, QUIET, "middle"); text(370, 504, "otlp to jaeger :4317", 11.5, 400, QUIET, "middle")
named(516, 260, 204, 88, STORE, "Prometheus", ["18 SLO + alert rules", "30-day retention, 10Gi PVC"])
named(516, 372, 204, 56, UI, "Alertmanager", ["page or ticket"])
named(516, 452, 204, 72, STORE, "Jaeger v2", ["OTLP in, query API :16686", "20k traces in memory"])
named(264, 556, 456, 56, UI, "Grafana", ["dashboards and Explore: metrics next to traces"])
# connectors (broken around badges)
for d, a in [("M220 128H245", False), ("M265 128H290", True), ("M470 128H495", False), ("M515 128H540", True),
             ("M132 316V340", True), ("M370 362V378", True), ("M370 438V454", True),
             ("M224 420H244V390", False), ("M244 370V340H280", True),
             ("M460 470H496V410", False), ("M496 390V304H516", True),
             ("M460 498H478", False), ("M498 498H516", True),
             ("M618 348V372", True), ("M618 524V556", True), ("M720 304H728V584H720", True)]:
    path(d, a)
path("M630 156V196", True, True)
text(140, 332, "HTTP", 11.5, 400, QUIET); text(646, 188, "sync", 11.5, 400, QUIET)
for cx, cy, c, n in [(255, 128, GIT, "1"), (505, 128, GIT, "2"), (612, 184, GIT, "3"), (244, 380, WORK, "4"),
                     (496, 400, STORE, "5"), (488, 498, PIPE, "6"), (598, 360, UI, "7"), (598, 540, UI, "8")]:
    badge(cx, cy, c, n)
# legend
legend = [(48, 668, GIT, "1", "Engineer pushes a change to GitHub"), (48, 692, GIT, "2", "Argo CD pulls the repo"),
          (48, 716, GIT, "3", "Argo CD syncs and self-heals every app"), (48, 740, WORK, "4", "App sends spans and metrics over OTLP"),
          (408, 668, STORE, "5", "Prometheus scrapes metrics from the Collector"), (408, 692, PIPE, "6", "Collector forwards traces to Jaeger"),
          (408, 716, UI, "7", "SLO burn-rate alerts go to Alertmanager"), (408, 740, UI, "8", "Grafana queries Prometheus and Jaeger")]
for cx, cy, c, n, s in legend:
    badge(cx, cy, c, n); text(cx + 18, cy + 4, s, 12)
for x, c, s in [(40, GIT, "GitOps"), (140, WORK, "Workloads"), (260, PIPE, "Telemetry pipeline"), (420, STORE, "Metrics and trace storage"), (604, UI, "Alerting and UI")]:
    add(f'<rect x="{x}" y="762" width="12" height="12" rx="3" fill="{c}" fill-opacity="0.25" stroke="{c}" stroke-width="1.25"/>')
    text(x + 18, 772, s, 11.5, 400, QUIET)
add("</svg>")
open(sys.argv[1], "w").write("\n".join(out) + "\n")
