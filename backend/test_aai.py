import asyncio
import httpx
from app.core.config import get_settings

settings = get_settings()

async def test_api():
    headers = {
        "authorization": settings.ASSEMBLYAI_API_KEY,
        "content-type": "application/json",
    }
    # Create a dummy audio url or just send invalid url to see parameter validation errors
    payload = {
        "audio_url": "https://example.com/audio.wav",
        "speech_models": ["nano"]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/transcript",
            headers=headers,
            json=payload,
        )
    print("speech_models=[nano]:", response.status_code, response.text)
    
    payload2 = {
        "audio_url": "https://example.com/audio.wav",
        "speech_model": "nano"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.ASSEMBLYAI_BASE_URL}/v2/transcript",
            headers=headers,
            json=payload2,
        )
    print("speech_model='nano':", response.status_code, response.text)

if __name__ == "__main__":
    asyncio.run(test_api())
