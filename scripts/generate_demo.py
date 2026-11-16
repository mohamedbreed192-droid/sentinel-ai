"""Run real scanners on the synthetic fixture and update both demo consumers."""
from pathlib import Path
import json
from sentinel.pipeline import analyze_directory
root=Path(__file__).resolve().parents[1]
report=analyze_directory(root/"fixtures/demo",{"name":"sentinel-labs/reliability-demo","url":"https://github.com/example/synthetic-fixture","description":"Intentionally vulnerable synthetic fixture"},demo=True)
for path in [root/"backend/sentinel/demo.json",root/"frontend/app/demo.json"]:
    path.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"findings":len(report["findings"]),"coverage":report["coverage"]},indent=2))
