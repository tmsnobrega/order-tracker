# Express-order lookup incident

## What failed

The app stayed healthy, but opening `express-1002` returned HTTP 500. Its
delivery estimate used a day number that did not exist in the order's month.
The seeded order was dated 31 August 2026. Adding two to the day field produced
33 August instead of 2 September.

I recorded the failing requests in [incident-trigger.json](evidence/incident-trigger.json).
The metric counted 5xx responses on `/api/orders/{order_id}`. The error trace
contained the `ValueError` and the failing line in `order_detail`.

## How the automatic response worked

Grafana evaluated the one-minute server-error window and sent its firing
notification to the host responder. The responder saved the notification,
metrics, logs, trace search results, and an error trace before starting Codex.
The successful run was `20260930T092224Z-a9352aed`.

The agent received the saved evidence and current source as untrusted input.
It ran in read-only mode and returned a JSON repair proposal. The observed CLI
was Codex 0.159.2, using `gpt-6.1-sol`. No model override was supplied. The
runtime configuration and original response are saved with the incident.

The responder allowed only the known one-line calendar repair in `app/main.py`.
It required `ALLOW_LOCAL_FIX=1`, a unique text replacement, valid Python, and
passing tests against an isolated copy of the candidate. The candidate passed
13 checks, including month-end, leap-year, year-end, standard-order, and API
behavior checks. The agent had no deployment access.

The responder then applied the approved proposal and ran
`docker compose up --build -d --wait app`. The deployment used the telemetry
version `hw04-fixed`. The same express lookup returned 200 and the expected
date `2026-09-02`. The alert returned to Normal after the error window cleared.

The saved [incident evidence](../incident-response/evidence/20260930T092224Z-a9352aed/evidence.json),
[proposal](../incident-response/evidence/20260930T092224Z-a9352aed/agent-answer.txt),
[change](../incident-response/evidence/20260930T092224Z-a9352aed/change.diff),
[policy decision](../incident-response/evidence/20260930T092224Z-a9352aed/policy.json),
and [recovery result](../incident-response/evidence/20260930T092224Z-a9352aed/recovery.json)
show this sequence.

## Problems found while setting it up

The first Grafana rule used an incorrectly escaped expression. I changed
`$$A > 0` to `$A > 0` in the query model and verified Normal evaluation.
An early trace query also timed out during startup. The final check selects
the specific 404 trace and log instead of accepting any service signal.

The first real responder attempt hit Windows' command-length limit. Passing
the prompt through standard input resolved that. Another attempt identified
the correct fix but could not edit files under the managed agent permissions.
I changed the design to a read-only proposal with separate application and
deployment checks. This kept the permission restriction intact.

The candidate tests initially hit permissions on a shared Windows temporary
directory. Each incident now has its own test directory. A responder restart
also interrupted one investigation. Startup now marks unfinished runs as
escalated instead of leaving them shown as investigating. Failed attempts did
not deploy a repair. Their full local records are retained, but only the test
notification and successful incident packet are included in the published
homework to avoid repeating the same telemetry.

## Limits of this exercise

This is a single-process local responder, not a production on-call system.
All published ports are bound to localhost, but there is no webhook
authentication or durable task queue. The repair policy is deliberately limited
to this calendar bug. Unknown alerts, other code changes, or failed checks
require manual review. It does not automatically solve arbitrary incidents.

The app uses one SQLite container. Telemetry history is stored in container-local
files. Recreating those containers can clear it. Saved incident evidence is
separate from that live history.

Metrics and request logs omit customer names, request bodies, and order IDs.
Traces may include exception details and source paths. The sample data here is
synthetic. Real production evidence would need a separate review before being
sent to an external model or published.
