# Order Tracker: Homework 04

I used Order Tracker to investigate a failed express-order lookup. The app could
pass its health check while an order request returned a server error. My homework
adds request telemetry, a Grafana dashboard and alert, and a local responder that
asks Codex to investigate the incident.

The app comes from [Alexey Grigorev's starter](https://github.com/alexeygrigorev/order-tracker),
commit `72de4478257813e3ca3a285988f3ad759ec4ea8d`. I kept the starter's small
FastAPI and SQLite setup. This is a local course exercise, with one app container
and synthetic sample orders.

## Run the app and dashboard

Requirements: Docker with Compose, Python 3.11 or later, and `uv`. The pinned
Collector image targets Linux amd64, as used by Docker Desktop on this machine.

```powershell
docker compose up --build -d --wait
uv sync --frozen
```

Open the app at <http://127.0.0.1:8000> and the dashboard at
<http://127.0.0.1:3000/d/order-tracker/order-tracker>. Grafana allows local
read-only viewing without a login. Its data sources and alert are provisioned
from the files in `observability/`.

The app exports metrics, logs, and traces through the OpenTelemetry Collector.
Prometheus stores metrics, Loki stores logs, and Tempo stores traces. The request
metric uses the route template and status code. It does not include customer
names, order IDs, or request bodies in its labels.

To inspect console exports separately:

```powershell
docker compose -f compose.yaml -f compose.console.yaml up --build -d --wait app
uv run --frozen python tools/capture_console.py
docker compose up --build -d --wait app
```

## Start the local incident responder

Install the official Codex CLI and sign in with `codex login` on the host first.
The responder uses the existing login. No credential belongs in this repository.
For Windows PowerShell:

```powershell
$env:ALLOW_LOCAL_FIX = '1'
uv run --frozen uvicorn responder:app --app-dir incident-response --host 127.0.0.1 --port 8001
```

This host responder was verified on Windows. Other operating systems may need
changes to the CLI lookup and environment setup. Docker Desktop lets Grafana reach the host through
`host.docker.internal`. Other Docker setups may need a host binding appropriate
to their network. Do not expose this responder to the internet.

Grafana watches order-lookup 5xx responses in a one-minute window and evaluates
every ten seconds. A missing order returns 404 and should not fire this alert.
The notification includes the endpoint, time window, and dashboard link.

The responder saves the alert and telemetry, then starts `codex exec` in
read-only mode. The agent returns a structured repair proposal. Separate code
checks the proposal against the one allowed calendar repair, tests a copy of the
app, and then rebuilds only the app service. `ALLOW_LOCAL_FIX` must be `1` for
that repair to be allowed. Other changes or failed checks are escalated without
deployment. The agent itself cannot deploy the app.

See `/incidents` on port 8001 for the recorded status. Evidence is saved under
`incident-response/evidence/`. Workspaces and verbose CLI output stay local and
are excluded from Git.

To send the homework's test notification in PowerShell:

```powershell
$body = '{"alerts":[{"status":"firing","labels":{"alertname":"ResponderTest","test":"true"},"annotations":{"summary":"Test notification; no incident to fix"}}]}'
Invoke-RestMethod -Uri http://127.0.0.1:8001/alerts -Method Post -ContentType application/json -Body $body
```

The committed app includes the fix, so `express-1002` should now return 200.
`tools/trigger_incident.py` was used against the original failing calculation
and expects at least one 500. It is not a health check for the fixed version.

## Checks and results

```powershell
uv run --frozen pytest -q tests incident-response/contract_test.py
uv run --frozen python tools/check_stack.py
```

The calendar tests cover month-end, leap-year, and year-end dates. The API tests
cover seeded orders, creation, status updates, and missing orders. Additional
tests check telemetry status labels and rejected responder payloads.

Read [my homework answers](docs/homework-answers.md),
[the incident report](docs/incident-report.md), and
[the validation record](docs/validation.md) for the observed results.

Stop the stack with `docker compose down`. The orders volume is retained.
Grafana and telemetry storage in this exercise use container-local files, so
recreating those containers can clear their history. Saved evidence remains in
the repository.
