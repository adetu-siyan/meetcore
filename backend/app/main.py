"""
MeetCore — FastAPI Entry Point
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import upload, nio_chat, tts, realtime_token, stt, tools

app = FastAPI(title="MeetCore API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(nio_chat.router)
app.include_router(tts.router)
app.include_router(realtime_token.router)
app.include_router(stt.router)
app.include_router(tools.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "MeetCore API"}