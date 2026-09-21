# Backend addition needed

Add this route to your FastAPI backend (app/routers/upload.py or a new file):

```python
@router.post("/realtime-token")
async def get_realtime_token():
    """
    Generates a short-lived AssemblyAI token for browser streaming STT.
    Never expose ASSEMBLYAI_API_KEY directly in the frontend.
    """
    import httpx
    headers = {
        "authorization": settings.ASSEMBLYAI_API_KEY,
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/realtime/token",
            headers=headers,
            json={"expires_in": 3600},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not generate token")
    return response.json()  # { token }
```
