"""Verify the deployed calendar fix and save a compact final validation record."""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx

root = Path(__file__).resolve().parents[1]
(root / ".runtime").mkdir(exist_ok=True)
tests = subprocess.run([sys.executable, "-m", "pytest", "-q", "--tb=short",
                        "--disable-warnings", "-p", "no:cacheprovider",
                        "--basetemp", str(root / ".runtime" / ("qa-" + uuid4().hex)),
                        "tests", "incident-response/contract_test.py"], cwd=root,
                       capture_output=True, text=True)
assert tests.returncode == 0, tests.stdout + tests.stderr
results = {}
for order_id, expected in [("standard-1001", 200), ("standard-1002", 404), ("express-1002", 200)]:
    response = httpx.get("http://127.0.0.1:8000/api/orders/" + order_id, timeout=15)
    assert response.status_code == expected
    results[order_id] = response.status_code
    if order_id == "express-1002":
        order = response.json()
        assert order["estimated_delivery"] == (datetime.fromisoformat(order["created_at"]) + timedelta(days=2)).date().isoformat()
        results["estimated_delivery"] = order["estimated_delivery"]
for _ in range(4):
    assert httpx.get("http://127.0.0.1:8000/api/orders/express-1002", timeout=15).status_code == 200
health = httpx.get("http://127.0.0.1:8000/healthz", timeout=15).json()
assert health == {"status": "ok"}
rules = httpx.get("http://127.0.0.1:3000/api/prometheus/grafana/api/v1/rules", timeout=30)
rules.raise_for_status()
rule = rules.json()["data"]["groups"][0]["rules"][0]
assert rule["health"] == "ok"
assert rule["state"] == "inactive", rule
proof = {"checked_at": datetime.now(timezone.utc).isoformat(), "health": health,
         "requests": results, "express_repeat_checks": 5,
         "tests": tests.stdout.strip().splitlines()[-1],
         "alert": {"state": "Normal", "health": rule["health"], "last_evaluation": rule["lastEvaluation"]}}
(root / "docs/evidence/final-validation.json").write_text(json.dumps(proof, indent=2) + "\n")
print(json.dumps(proof, indent=2))
