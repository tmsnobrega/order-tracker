"""Check the stored signals through Grafana's configured data sources."""
import json
import time
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]
proxy = "http://127.0.0.1:3000/api/datasources/proxy/uid/"
response = httpx.get("http://127.0.0.1:8000/api/orders/standard-1002")
assert response.status_code == 404
time.sleep(12)

def query(source, endpoint, params):
    response = httpx.get(proxy + source + endpoint, params=params, timeout=30)
    response.raise_for_status()
    return response.json()

metrics = query("prometheus", "/api/v1/query", {"query":
    'http_server_requests_total{http_route="/api/orders/{order_id}",http_response_status_code="404"}'})
assert metrics["data"]["result"], "The 404 request metric is missing"
logs = query("loki", "/loki/api/v1/query_range", {"query": '{service_name="order-tracker"}', "limit": 20})
assert logs["data"]["result"], "The request logs are missing"
traces = query("tempo", "/api/search", {"q": '{resource.service.name="order-tracker"}', "limit": 20})
assert traces.get("traces"), "The request traces are missing"
rules_response = httpx.get("http://127.0.0.1:3000/api/prometheus/grafana/api/v1/rules")
rules_response.raise_for_status()
rules = rules_response.json()
out = root / "docs/evidence/stored-telemetry.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"http_status": 404, "metrics": metrics, "logs": logs, "traces": traces, "alert_rules": rules}, indent=2) + "\n")
print("Question 3: 404; metrics, logs, and traces are available through Grafana.")
print("Question 4 alert rules:", json.dumps(rules)[-1000:])
