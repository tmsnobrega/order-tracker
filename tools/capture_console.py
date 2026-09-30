"""Capture the actual console exporters for Homework 04 Question 2."""
import json
import subprocess
import time
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]
response = httpx.get("http://127.0.0.1:8000/api/orders/standard-1001")
assert response.status_code == 200
time.sleep(8)
result = subprocess.run(["docker", "compose", "logs", "--no-log-prefix", "--since", "30s", "app"],
                        cwd=root, capture_output=True, text=True, check=True)
decoder = json.JSONDecoder()
documents = []
text = result.stdout
while text:
    start = text.find("{")
    if start < 0:
        break
    try:
        value, end = decoder.raw_decode(text[start:])
        documents.append(value)
        text = text[start + end:]
    except ValueError:
        text = text[start + 1:]
metrics = [d for d in documents if "resource_metrics" in d]
assert any('"http.response.status_code": 200' in json.dumps(d) for d in metrics)
out = root / "docs/evidence/console-telemetry.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"http_status": response.status_code, "telemetry": documents}, indent=2) + "\n")
print("Question 2: HTTP 200; the console request metric records 200.")
