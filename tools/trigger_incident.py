"""Repeat the seeded failing lookup and record the actual HTTP outcomes."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

root = Path(__file__).resolve().parents[1]
outcomes = []
for _ in range(20):
    response = httpx.get("http://127.0.0.1:8000/api/orders/express-1002", timeout=10)
    outcomes.append({"at": datetime.now(timezone.utc).isoformat(), "http_status": response.status_code})
    time.sleep(1)
assert any(row["http_status"] == 500 for row in outcomes), "The original failure was not reproduced"
path = root / "docs/evidence/incident-trigger.json"
path.write_text(json.dumps({"endpoint": "/api/orders/express-1002", "requests": outcomes}, indent=2) + "\n")
print("Failing lookup reproduced. Check /incidents for the real Grafana webhook.")
