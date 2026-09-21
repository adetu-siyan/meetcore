"""
MeetCore — Realtime Token
POST /realtime-token — mints a short-lived AssemblyAI streaming STT token.
Frontend uses this instead of holding the API key directly.
"""
import httpx
from fastapi import APIRouter, HTTPException
from urllib.parse import urlencode
from app.core.config import get_settings

router = APIRouter(prefix="/realtime-token", tags=["realtime"])
settings = get_settings()


@router.post("")
async def get_realtime_token():
    headers = {"Authorization": settings.ASSEMBLYAI_API_KEY}
    
    # AssemblyAI v3 streaming token endpoint uses GET with query parameters
    url = "https://streaming.assemblyai.com/v3/token"
    params = {"expires_in_seconds": 480}
    full_url = f"{url}?{urlencode(params)}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                full_url,
                headers=headers,
            )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"AssemblyAI token request failed: {e}")

    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AssemblyAI error {r.status_code}: {r.text}",
        )

    return r.json()  # {"token": "..."}