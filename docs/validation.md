# Validation record

I ran these checks on 30 September 2026 using Windows PowerShell and Docker
Desktop. The source started from upstream commit
`72de4478257813e3ca3a285988f3ad759ec4ea8d`.

## Commands and observed results

1. `docker compose up --build -d --wait`: the original app started and
   `GET /healthz` returned `{"status":"ok"}`. The original API suite passed
   three tests.
2. `docker compose -f compose.yaml -f compose.console.yaml up --build -d --wait app`,
   followed by `uv run --frozen python tools/capture_console.py`: the real
   `standard-1001` lookup returned 200 and the console request metric recorded 200.
3. `docker compose up --build -d --wait`: the app, Collector, Prometheus, Loki,
   Tempo, and Grafana started. `uv run --frozen python tools/check_stack.py`
   verified the 404 metric, log, and trace through Grafana's data sources.
   Grafana's evaluated alert was Normal and healthy.
4. The supplied JSON notification was posted to `http://127.0.0.1:8001/alerts`.
   It returned 202. The automatically started agent completed with the last
   line `No incident to fix.`
5. `uv run --frozen python tools/trigger_incident.py`: repeated requests to
   `express-1002` returned 500. Grafana sent a real firing webhook. In the
   successful run, the responder accepted the agent's proposal after 13
   candidate checks passed, rebuilt the app, and verified a 200 response.
6. `uv run --frozen python tools/check_recovery.py`: the final recorded checks
   cover the complete test suite, five successful express lookups, the exact
   delivery date, a missing-order 404, a standard-order 200, the health check,
   and the healthy Normal alert. See [final-validation.json](evidence/final-validation.json)
   for the actual test count and timestamp.

The dashboard was also opened in the browser. Its request and error charts
loaded, along with request logs. The dashboard uses estimated request counts
from Prometheus `increase` over one minute, so displayed values can be fractional
because Prometheus extrapolates between samples.

## Review notes

The successful source diff changes only the delivery calculation from
`replace(day=...)` to `timedelta(days=2)`. No database rows were deleted and no
schema change was needed. Standard orders still have no delivery estimate.
The trusted calendar contract is separate from the agent's proposal.

The tests report a Starlette/httpx deprecation warning. It does not fail the
checks. The pinned Collector also reports deprecated configuration aliases.
Those aliases worked in the verified stack. A dependency upgrade would need
another stack check.

I kept credentials, virtual environments, temporary databases, incident
workspaces, and verbose CLI output out of the published files. The original
agent responses and saved telemetry are unchanged.
