import requests, json, logging
logging.disable(logging.CRITICAL)

BASE = "http://localhost:8010/api/v1"

# 1. Check existing lineage BEFORE trigger
print("=== Before governance trigger ===")
r = requests.get(f"{BASE}/governance/lineage", timeout=10)
before = r.json()
print(f"Existing lineage records: {len(before)}")
for item in before[:3]:
    print(f"  target_id={item['target_id']} step={item['transform_step']} source_id={item['source_id']}")

# 2. Trigger governance for a specific video with comments
print("\n=== Triggering governance for BV1RhdtYDEyd ===")
r = requests.post(f"{BASE}/governance/trigger", params={"video_bvid": "BV1RhdtYDEyd"}, timeout=30)
result = r.json()
print(f"Status: {result['status']}, results: {result['results']}, total_processed: {result['total_processed']}")

# 3. Check lineage AFTER trigger
print("\n=== After governance trigger ===")
r = requests.get(f"{BASE}/governance/lineage", timeout=10)
after = r.json()
print(f"Total lineage records: {len(after)}")
new_records = [item for item in after if item not in before]
print(f"New records since trigger: {len(new_records)}")
for item in after[:5]:
    print(f"  target_id={item['target_id']} step={item['transform_step']} source_id={item['source_id']}")

# 4. Verify the response structure
print("\n=== Record structure check ===")
if after:
    item = after[0]
    print(f"Fields: {list(item.keys())}")
    print(f"Sample: {json.dumps(item, ensure_ascii=False)}")