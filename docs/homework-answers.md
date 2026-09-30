# Homework 04 answers

I used the [official Homework 04 instructions](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/cohorts/2026/homework/04-devops/homework.md)
and checked the running app before recording these answers on 30 September 2026.

## 1. Health check

Answer: `{"status":"ok"}`.

`GET /healthz` returned this response. The health check tests database access.
It did not detect the express-order date bug.

## 2. Console request metric

Answer: `200`.

`GET /api/orders/standard-1001` returned 200. The console metric recorded
`http.route=/api/orders/{order_id}` and `http.response.status_code=200`.
The captured export is in [console-telemetry.json](evidence/console-telemetry.json).

## 3. Request metric in Grafana

Answer: `404`.

There is no seeded order called `standard-1002`. I checked its 404 metric through
Grafana's Prometheus data source, along with the matching 404 log and trace
through Loki and Tempo. See [stored-telemetry.json](evidence/stored-telemetry.json).

## 4. Server-error alert

Answer: `Normal`.

The missing-order lookup is a 404, not a 5xx response. Grafana showed Normal
after evaluating it. The alert checks server errors in a one-minute window.
The query returns zero when no 5xx series exists, and the rule uses OK for no data.

## 5. Automatic responder test

The responder started Codex automatically after receiving the supplied test
notification. The agent said no repair was needed. It also reported that its
attempt to read the evidence file was blocked by policy. It changed no files
and called no services.

The last line was:

```text
No incident to fix.
```

The [original agent response](../incident-response/evidence/20260930T090042Z-7b6367db/agent-answer.txt)
is kept unchanged as evidence.

## 6. Root cause and recovery

Answer: The express delivery date calculation tried to use a day that does not
exist in that month.

The original code used `placed_at.replace(day=placed_at.day + 2)`. For the
seeded order dated 31 August 2026, that attempted to create 33 August. The
request failed with `ValueError: day is out of range for month` and HTTP 500.

Codex proposed `placed_at + timedelta(days=2)`. The responder checked the
proposal, passed 13 candidate tests, applied the one-line fix, and rebuilt the
app. The same order then returned HTTP 200 with delivery date `2026-09-02`.
See [the incident report](incident-report.md) and
[the recovery evidence](../incident-response/evidence/20260930T092224Z-a9352aed/recovery.json).

## Submission

Implementation repository: <https://github.com/tmsnobrega/order-tracker>.

Course workspace: <https://github.com/tmsnobrega/ai-dev-zoomcamp-2026/tree/main/hw04-devops>.

Submission form: <https://courses.datatalks.club/ai-dev-tools-2026/homework/hw4>.
The form displayed 6 October 2026 at 01:00 in the Europe/Amsterdam timezone.
