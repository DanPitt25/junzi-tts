#!/usr/bin/env python3
"""
Junzi TTS Server - Text-to-speech for Classical Chinese

Usage:
    pip install edge-tts aiohttp
    python server.py
"""

import hashlib
import io
import os
from pathlib import Path

import edge_tts
from aiohttp import web

# === Configuration ===
CACHE_DIR = Path("cache/tts")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Available Chinese voices
VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "yunxi": "zh-CN-YunxiNeural",
    "yunyang": "zh-CN-YunyangNeural",
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "xiaochen": "zh-TW-HsiaoChenNeural",
    "yunjhe": "zh-TW-YunJheNeural",
}
DEFAULT_VOICE = "yunxi"
DEFAULT_RATE = "-10%"


def tts_cache_key(text: str, voice: str, rate: str) -> str:
    h = hashlib.sha256(f"{text}|{voice}|{rate}".encode()).hexdigest()[:16]
    return h


async def handle_tts(request: web.Request) -> web.StreamResponse:
    """Generate TTS audio for given text."""
    text = request.query.get("text", "").strip()
    voice_key = request.query.get("voice", DEFAULT_VOICE)
    rate = request.query.get("rate", DEFAULT_RATE)

    if not text:
        return web.json_response({"error": "No text provided"}, status=400)

    voice = VOICES.get(voice_key, VOICES[DEFAULT_VOICE])
    key = tts_cache_key(text, voice, rate)
    cached_path = CACHE_DIR / f"{key}.mp3"

    if cached_path.exists():
        return web.FileResponse(
            cached_path,
            headers={
                "Content-Type": "audio/mpeg",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=86400",
            },
        )

    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])

        audio_bytes = audio_data.getvalue()
        if not audio_bytes:
            return web.json_response({"error": "No audio generated"}, status=500)

        cached_path.write_bytes(audio_bytes)

        return web.Response(
            body=audio_bytes,
            content_type="audio/mpeg",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=86400",
            },
        )
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_voices(request: web.Request) -> web.Response:
    """Return available voices."""
    voice_list = [{"key": k, "name": v} for k, v in VOICES.items()]
    return web.json_response(voice_list, headers={"Access-Control-Allow-Origin": "*"})


async def handle_options(request: web.Request) -> web.Response:
    """Handle CORS preflight."""
    return web.Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )


async def handle_health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response({"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/tts", handle_tts)
    app.router.add_get("/api/voices", handle_voices)
    app.router.add_route("OPTIONS", "/api/{path:.*}", handle_options)
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Junzi TTS Server running on port {port}")
    web.run_app(create_app(), port=port, print=None)
