import requests
r = requests.get("http://localhost:8010/governance", timeout=10)
html = r.text
# Check key markers
checks = [
    "chart-lineage",
    "lineage-summary",
    "loadLineage",
    "window._lineageChart",
    "document.getElementById('lineage-summary')",
]
for ck in checks:
    print(f"  {'[OK]' if ck in html else '[MISSING]'} {ck}")