import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"
MEETING_ID = "test_meeting_id"  # Usually we'd need a real one

async def test_endpoint(name, path, payload):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{BASE_URL}{path}", json=payload, timeout=5.0)
            print(f"[{name}] HTTP {res.status_code}")
            try:
                print("Response:", json.dumps(res.json(), indent=2)[:200])
            except:
                print("Response:", res.text[:200])
    except Exception as e:
        print(f"[{name}] Failed: {e}")
    print("-" * 40)

async def main():
    print("Testing MeetCore Tools in Terminal...\n")
    
    payload = {"meeting_id": MEETING_ID}
    
    await test_endpoint("Transcript", "/tools/transcript", payload)
    await test_endpoint("Summary", "/tools/summary", payload)
    await test_endpoint("Action Items", "/tools/action-items", payload)
    await test_endpoint("Draft Email", "/tools/draft-email", {"meeting_id": MEETING_ID, "instruction": "Test"})
    await test_endpoint("Schedule Meeting", "/tools/schedule-meeting", payload)

if __name__ == "__main__":
    asyncio.run(main())
