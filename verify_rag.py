"""
verify_rag.py — End-to-end RAG + API integration test script.

Run this AFTER starting the FastAPI server (npm start) and PostgreSQL.

Usage:
    python verify_rag.py
"""

import sys
import json
import httpx

BASE_URL = "http://localhost:8000"
TIMEOUT = 90.0  # Ollama can be slow on first call

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

errors = []


def check(label: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  {PASS} {label}")
    else:
        msg = f"  {FAIL} {label}" + (f" — {detail}" if detail else "")
        print(msg)
        errors.append(msg)


# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  AI Travel Planner — RAG & API Integration Test")
print("="*60 + "\n")

client = httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)

# ── Test 1: Health Check ──────────────────────────────────────────────────────
print("[1/6] GET /health")
try:
    r = client.get("/health")
    check("Status code is 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()
    check("Response has 'status' field", "status" in data)
    check("Response has 'database' field", "database" in data)
    check("Response has 'timestamp' field", "timestamp" in data)
    print(f"  {INFO} DB status: {data.get('database')}")
    print(f"  {INFO} Overall:   {data.get('status')}")
except Exception as e:
    print(f"  {FAIL} Health check error: {e}")
    errors.append(str(e))

# ── Test 2: Add Data ───────────────────────────────────────────────────────────
print("\n[2/6] POST /add-data (RAG seed for Munnar test)")
munnar_payload = {
    "name": "Munnar",
    "description": (
        "Secret Valley Waterfall is a hidden gem in Munnar, Kerala. "
        "Located 14 km off the main road, it requires a 45-minute trek through "
        "cardamom and tea plantations. Very few tourists visit it."
    ),
    "category": "place"
}
try:
    r = client.post("/add-data", json=munnar_payload)
    check("Status code is 201", r.status_code == 201, f"got {r.status_code} — {r.text[:200]}")
    if r.status_code == 201:
        data = r.json()
        check("Response has 'id'",   "id"   in data)
        check("Response has 'name'", "name" in data)
        check("Name matches",        data.get("name") == "Munnar")
        print(f"  {INFO} Inserted entry ID: {data.get('id')}")
except Exception as e:
    print(f"  {FAIL} /add-data error: {e}")
    errors.append(str(e))

# ── Test 3: RAG Chat — Must Retrieve Inserted Entry ───────────────────────────
print("\n[3/6] POST /chat — RAG retrieval test ('Tell me hidden places in Munnar')")
try:
    r = client.post("/chat", json={"query": "Tell me hidden places in Munnar"})
    check("Status code is 200", r.status_code == 200, f"got {r.status_code} — {r.text[:200]}")
    if r.status_code == 200:
        data = r.json()
        check("Response has 'response' field", "response" in data)
        response_text = data.get("response", "").lower()
        rag_hit = "secret valley" in response_text or "waterfall" in response_text or "hidden" in response_text
        check(
            "RAG context retrieved — response mentions 'Secret Valley' or 'waterfall'",
            rag_hit,
            f"Got: {data.get('response', '')[:200]}"
        )
        print(f"  {INFO} LLM response: {data.get('response', '')[:300]}")
except Exception as e:
    print(f"  {FAIL} /chat error: {e}")
    errors.append(str(e))

# ── Test 4: Weather ────────────────────────────────────────────────────────────
print("\n[4/6] GET /weather/tokyo")
try:
    r = client.get("/weather/tokyo")
    check("Status code is 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        check("Has 'city'",        "city"        in data)
        check("Has 'temperature'", "temperature" in data)
        check("Has 'humidity'",    "humidity"    in data)
        check("Has 'wind_speed'",  "wind_speed"  in data)
        print(f"  {INFO} Weather: {data}")
except Exception as e:
    print(f"  {FAIL} /weather error: {e}")
    errors.append(str(e))

# ── Test 5: Plan Trip ──────────────────────────────────────────────────────────
print("\n[5/6] POST /plan-trip (Tokyo, 2 days, Moderate)")
trip_payload = {
    "destination": "Tokyo",
    "budget": "Moderate",
    "days": 2,
    "preferences": "temples and local food"
}
try:
    r = client.post("/plan-trip", json=trip_payload)
    check("Status code is 200", r.status_code == 200, f"got {r.status_code} — {r.text[:300]}")
    if r.status_code == 200:
        data = r.json()
        check("Has 'destination'", "destination" in data)
        check("Has 'itinerary'",   "itinerary"   in data)
        itinerary = data.get("itinerary", [])
        check("Itinerary has 2 days",   len(itinerary) == 2, f"got {len(itinerary)}")
        if itinerary:
            day1 = itinerary[0]
            check("Day 1 has 'theme'",         "theme"         in day1)
            check("Day 1 has 'activities'",    "activities"    in day1)
            check("Day 1 has 'recommended_food'", "recommended_food" in day1)
            check("Day 1 has 'estimated_cost'","estimated_cost" in day1)
        print(f"  {INFO} Itinerary preview: {json.dumps(itinerary[0], indent=2)[:400]}" if itinerary else "")
except Exception as e:
    print(f"  {FAIL} /plan-trip error: {e}")
    errors.append(str(e))

# ── Test 6: Edge Cases ─────────────────────────────────────────────────────────
print("\n[6/6] Edge case — POST /plan-trip with days=0 (must reject)")
try:
    r = client.post("/plan-trip", json={"destination": "Tokyo", "budget": "Budget", "days": 0})
    check("Invalid days=0 returns 422", r.status_code == 422, f"got {r.status_code}")
except Exception as e:
    print(f"  {FAIL} Edge case error: {e}")
    errors.append(str(e))

# ── Summary ────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
if errors:
    print(f"  RESULT: {len(errors)} test(s) FAILED")
    for e in errors:
        print(f"    {e}")
    sys.exit(1)
else:
    print("  RESULT: ALL TESTS PASSED")
print("="*60 + "\n")

client.close()
