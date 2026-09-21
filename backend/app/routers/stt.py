"""
MeetCore — STT Router
POST /stt — live mic blob → PCM16 via ffmpeg → AssemblyAI v3 WebSocket → transcript

Push-to-talk: user holds, speaks, releases. We convert the blob to PCM16,
blast all chunks as fast as possible, terminate immediately, then take
whatever transcript we have at Termination — no waiting for end_of_turn.
~300–600ms vs 3–8s with the REST approach.
"""
import asyncio
import json

import websockets
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/stt", tags=["stt"])
settings = get_settings()

ASSEMBLYAI_WS_URL = "wss://streaming.assemblyai.com/v3/ws"
SAMPLE_RATE       = 16000
CHUNK_SIZE        = 4096


class STTResponse(BaseModel):
    text: str


async def _webm_to_pcm16(webm_bytes: bytes) -> bytes:
    """webm/opus → raw PCM16 mono 16kHz via ffmpeg."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i", "pipe:0",
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ar", str(SAMPLE_RATE),
            "-ac", "1",
            "-loglevel", "error",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=webm_bytes),
            timeout=15.0,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr.decode()[:200]}")
        return stdout
    except asyncio.TimeoutError:
        raise RuntimeError("ffmpeg timed out")


async def _stream_to_assemblyai(pcm_bytes: bytes) -> str:
    """
    Blast full PCM blob to AssemblyAI v3 WebSocket, terminate immediately,
    return the best transcript at Termination.

    We never wait for end_of_turn — since we control when audio ends via
    Terminate, we just take whatever Turn transcript we have when the
    session closes. This cuts latency from 3–8s to ~300–600ms.
    """
    if not pcm_bytes:
        return ""

    params = (
        f"?sample_rate={SAMPLE_RATE}"
        f"&encoding=pcm_s16le"
        f"&speech_model=universal-streaming-english"
        f"&format_turns=true"
    )
    headers = {"Authorization": settings.ASSEMBLYAI_API_KEY}

    best_transcript = ""

    try:
        async with websockets.connect(
            ASSEMBLYAI_WS_URL + params,
            additional_headers=headers,
            open_timeout=10,
            ping_interval=None,
            close_timeout=10,
            max_size=10 * 1024 * 1024,
        ) as ws:

            # ── Wait for Begin ───────────────────────────────────────────────
            raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
            msg = json.loads(raw)
            if msg.get("type") != "Begin":
                raise RuntimeError(f"Expected Begin, got: {msg}")
            print(f"[STT] session {msg.get('id')} open", flush=True)

            # ── Blast all audio as fast as possible ──────────────────────────
            offset = 0
            while offset < len(pcm_bytes):
                chunk   = pcm_bytes[offset: offset + CHUNK_SIZE]
                offset += CHUNK_SIZE
                await ws.send(chunk)

            # ── Terminate immediately ────────────────────────────────────────
            await ws.send(json.dumps({"type": "Terminate"}))
            print(f"[STT] sent {len(pcm_bytes)} bytes + Terminate", flush=True)

            # ── Collect until Termination — take best Turn seen ──────────────
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue

                msg_type = msg.get("type", "")
                print(f"[STT] {msg_type}: {msg}", flush=True)

                if msg_type == "Turn":
                    text = msg.get("transcript", "").strip()
                    if text:
                        # Always overwrite — last Turn before Termination
                        # is the most complete transcript
                        best_transcript = text

                elif msg_type == "Termination":
                    break

                elif msg_type == "Error":
                    print(f"[STT] server error: {msg}", flush=True)
                    break

    except websockets.exceptions.InvalidHandshake as e:
        raise HTTPException(status_code=502, detail=f"STT handshake failed: {e}")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="STT WebSocket timed out")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"STT streaming failed: {e}")

    print(f"[STT] returning: '{best_transcript}'", flush=True)
    return best_transcript


@router.post("", response_model=STTResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    if len(audio_bytes) < 500:
        raise HTTPException(status_code=400, detail="Audio too short — hold the mic longer.")

    print(f"[STT] received {len(audio_bytes)} bytes", flush=True)

    try:
        pcm_bytes = await _webm_to_pcm16(audio_bytes)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not pcm_bytes or len(pcm_bytes) < 100:
        raise HTTPException(status_code=422, detail="Audio conversion produced no output.")

    print(f"[STT] PCM bytes: {len(pcm_bytes)}", flush=True)

    transcript = await _stream_to_assemblyai(pcm_bytes)
    return STTResponse(text=transcript.strip())
# """
# MeetCore — STT Router
# POST /stt — live mic blob → AssemblyAI REST API → transcript

# Push-to-talk: user holds button, speaks, releases. Complete blob is sent.
# We upload the raw webm directly — AAI REST supports it natively.
# No ffmpeg conversion needed, no turn-detection, no pausing at full stops.
# """
# import asyncio

# import httpx
# from fastapi import APIRouter, File, HTTPException, UploadFile
# from pydantic import BaseModel

# from app.core.config import get_settings

# router = APIRouter(prefix="/stt", tags=["stt"])
# settings = get_settings()

# ASSEMBLYAI_BASE = "https://api.assemblyai.com"


# class STTResponse(BaseModel):
#     """STTResponse model representing the transcription result.
    
#     Attributes:
#         text (str): The transcribed text."""
#     text: str


# async def _transcribe_rest(audio_bytes: bytes) -> str:
#     """
#     Upload raw webm blob to AssemblyAI REST, poll until complete, return transcript.
#     No turn detection — silence mid-sentence is never misread as end of speech.
#     """
#     auth_headers = {"authorization": settings.ASSEMBLYAI_API_KEY}

#     async with httpx.AsyncClient(timeout=30.0) as client:

#         # ── 1. Upload raw webm ────────────────────────────────────────────────
#         upload_res = await client.post(
#             f"{ASSEMBLYAI_BASE}/v2/upload",
#             headers={**auth_headers, "content-type": "application/octet-stream"},
#             content=audio_bytes,
#         )
#         if upload_res.status_code != 200:
#             raise HTTPException(
#                 status_code=502,
#                 detail=f"AAI upload failed ({upload_res.status_code}): {upload_res.text}",
#             )

#         audio_url = upload_res.json().get("upload_url")
#         if not audio_url:
#             raise HTTPException(status_code=502, detail="AAI upload returned no URL.")

#         print(f"[STT] uploaded → {audio_url}", flush=True)

#         # ── 2. Submit transcription job ───────────────────────────────────────
#         job_res = await client.post(
#             f"{ASSEMBLYAI_BASE}/v2/transcript",
#             headers=auth_headers,
#             json={
#                 "audio_url": audio_url,
#                 "speech_models": ["universal-3-pro", "universal-2"],
#                 "punctuate": True,
#                 "format_text": True,
#             },
#         )
#         if job_res.status_code != 200:
#             raise HTTPException(
#                 status_code=502,
#                 detail=f"AAI job failed ({job_res.status_code}): {job_res.text}",
#             )

#         job_id = job_res.json().get("id")
#         if not job_id:
#             raise HTTPException(status_code=502, detail="AAI job returned no ID.")

#         print(f"[STT] job submitted: {job_id}", flush=True)

#         # ── 3. Poll until complete ────────────────────────────────────────────
#         poll_url = f"{ASSEMBLYAI_BASE}/v2/transcript/{job_id}"

#         for attempt in range(40):  # max ~20s at 0.5s intervals
#             await asyncio.sleep(0.5)
#             poll_res = await client.get(poll_url, headers=auth_headers)

#             if poll_res.status_code != 200:
#                 raise HTTPException(
#                     status_code=502,
#                     detail=f"AAI poll failed ({poll_res.status_code}): {poll_res.text}",
#                 )

#             data = poll_res.json()
#             status = data.get("status")
#             print(f"[STT] poll {attempt + 1}: {status}", flush=True)

#             if status == "completed":
#                 text = (data.get("text") or "").strip()
#                 print(f"[STT] returning: '{text}'", flush=True)
#                 return text

#             if status == "error":
#                 raise HTTPException(
#                     status_code=502,
#                     detail=f"AAI transcription error: {data.get('error')}",
#                 )

#     raise HTTPException(status_code=504, detail="STT transcription timed out.")


# @router.post("", response_model=STTResponse)
# async def transcribe_audio(file: UploadFile = File(...)):
#     """Transcribe an uploaded audio file using the speech-to-text service.
    
#     Args:
#         file (UploadFile): The audio file uploaded by the client.
    
#     Returns:
#         STTResponse: A response object containing the transcribed text.
    
#     Raises:
#         HTTPException: If the uploaded file is empty or shorter than 500 bytes.
    
#     Side Effects:
#         Prints the size of the received audio data to standard output."""
#     audio_bytes = await file.read()

#     if not audio_bytes:
#         raise HTTPException(status_code=400, detail="Empty audio file.")
#     if len(audio_bytes) < 500:
#         raise HTTPException(status_code=400, detail="Audio too short — hold the mic longer.")

#     print(f"[STT] received {len(audio_bytes)} bytes", flush=True)

#     transcript = await _transcribe_rest(audio_bytes)
#     return STTResponse(text=transcript)
