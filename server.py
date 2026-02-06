#!/usr/bin/env python3
"""
Classical Chinese Reader - Backend Server

Handles:
1. TTS synthesis via edge-tts
2. Serving parallel Chinese-English texts from scraped translations

Usage:
    pip install edge-tts aiohttp
    python server.py

Server runs on http://localhost:8765
"""

import hashlib
import io
import os
import json
from pathlib import Path

import edge_tts
from aiohttp import web

# === Configuration ===
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
(CACHE_DIR / "tts").mkdir(exist_ok=True)
TRANSLATIONS_DIR = Path("translations")

# Cache for loaded translations
_translations_cache = {}

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


# === Translation Helpers ===

def load_translation(text_id: str) -> dict | None:
    """Load a translation JSON file, with caching."""
    if text_id in _translations_cache:
        return _translations_cache[text_id]

    path = TRANSLATIONS_DIR / f"{text_id}.json"
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        _translations_cache[text_id] = data
        return data
    except Exception as e:
        print(f"[Translation] Error loading {text_id}: {e}")
        return None


# === TTS Handlers ===

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
    cached_path = CACHE_DIR / "tts" / f"{key}.mp3"

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


# === Text API Handlers ===

async def handle_catalog(request: web.Request) -> web.Response:
    """Get the catalog of available texts."""
    # Define metadata for our translations
    translation_meta = {
        "analects": {"author": "孔子", "authorEn": "Confucius"},
        "mengzi": {"author": "孟子", "authorEn": "Mencius"},
        "daxue": {"author": "曾子", "authorEn": "Zengzi"},
        "zhongyong": {"author": "子思", "authorEn": "Zisi"},
        "daodejing": {"author": "老子", "authorEn": "Laozi"},
        "zhuangzi": {"author": "莊子", "authorEn": "Zhuangzi"},
        "mozi": {"author": "墨子", "authorEn": "Mozi"},
        "xunzi": {"author": "荀子", "authorEn": "Xunzi"},
        "hanfeizi": {"author": "韓非", "authorEn": "Han Fei"},
        "book-of-poetry": {"author": "", "authorEn": "Various"},
        "yijing": {"author": "", "authorEn": "Various"},
        "liji": {"author": "", "authorEn": "Various"},
        "shangshu": {"author": "", "authorEn": "Various"},
        "chunqiu-zuozhuan": {"author": "左丘明", "authorEn": "Zuo Qiuming"},
        "xiaojing": {"author": "", "authorEn": "Various"},
        "erya": {"author": "", "authorEn": "Various"},
        "liezi": {"author": "列子", "authorEn": "Liezi"},
        "guanzi": {"author": "管仲", "authorEn": "Guan Zhong"},
        "sunzi": {"author": "孫武", "authorEn": "Sun Tzu"},
        "yanzi-chunqiu": {"author": "晏嬰", "authorEn": "Yan Ying"},
        "huainanzi": {"author": "劉安", "authorEn": "Liu An"},
        "shiji": {"author": "司馬遷", "authorEn": "Sima Qian"},
    }

    # Auto-discover all translation files
    books = []
    translations_dir = Path("translations")
    if translations_dir.exists():
        for json_file in sorted(translations_dir.glob("*.json")):
            text_id = json_file.stem
            translation = load_translation(text_id)
            if translation and translation.get("chapters"):
                meta = translation_meta.get(text_id, {"author": "", "authorEn": ""})
                books.append({
                    "id": text_id,
                    "title": translation.get("title", ""),
                    "titleEn": translation.get("titleEn", ""),
                    "author": meta["author"],
                    "authorEn": meta["authorEn"],
                    "source": translation.get("source", ""),
                })

    return web.json_response({"books": books}, headers={"Access-Control-Allow-Origin": "*"})


async def handle_chapters(request: web.Request) -> web.Response:
    """Get chapters for a book."""
    book_id = request.query.get("id", "").strip()
    print(f"[Chapters] Request for book: {book_id}")

    if not book_id:
        return web.json_response({"error": "No book ID provided"}, status=400)

    translation = load_translation(book_id)
    if not translation:
        return web.json_response({"error": f"Book not found: {book_id}"}, status=404)

    chapters = []
    for ch in translation.get("chapters", []):
        chapters.append({
            "number": ch.get("number", ""),
            "title": ch.get("title", ""),
            "slug": ch.get("slug", ch.get("number", "")),
            "passageCount": len(ch.get("passages", []))
        })

    print(f"[Chapters] Found {len(chapters)} chapters")
    return web.json_response({
        "bookId": book_id,
        "chapters": chapters
    }, headers={"Access-Control-Allow-Origin": "*"})


async def handle_text(request: web.Request) -> web.Response:
    """Get text content for a chapter."""
    book_id = request.query.get("id", "").strip()
    chapter_num = request.query.get("chapter", "").strip()
    print(f"[Text] Request for book: {book_id}, chapter: {chapter_num}")

    if not book_id:
        return web.json_response({"error": "No book ID provided"}, status=400)

    translation = load_translation(book_id)
    if not translation:
        return web.json_response({"error": f"Book not found: {book_id}"}, status=404)

    # Find the chapter
    chapter_data = None
    for ch in translation.get("chapters", []):
        if ch.get("number") == chapter_num or ch.get("slug") == chapter_num:
            chapter_data = ch
            break

    if not chapter_data:
        # If no specific chapter requested, return all passages from all chapters
        if not chapter_num:
            all_passages = []
            for ch in translation.get("chapters", []):
                all_passages.extend(ch.get("passages", []))
            print(f"[Text] Returning all {len(all_passages)} passages")
            return web.json_response({
                "bookId": book_id,
                "title": translation.get("titleEn", ""),
                "passages": all_passages
            }, headers={"Access-Control-Allow-Origin": "*"})
        return web.json_response({"error": f"Chapter not found: {chapter_num}"}, status=404)

    passages = chapter_data.get("passages", [])
    print(f"[Text] Found {len(passages)} passages in chapter {chapter_num}")

    return web.json_response({
        "bookId": book_id,
        "chapter": chapter_num,
        "title": chapter_data.get("title", ""),
        "passages": passages
    }, headers={"Access-Control-Allow-Origin": "*"})


# === Utility Handlers ===

async def handle_options(request: web.Request) -> web.Response:
    """Handle CORS preflight."""
    return web.Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )


async def handle_health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response({"status": "ok"}, headers={"Access-Control-Allow-Origin": "*"})


# === Static File Serving ===

async def handle_index(request: web.Request) -> web.Response:
    """Serve the main HTML file."""
    index_path = Path(__file__).parent / "index.html"
    if index_path.exists():
        return web.FileResponse(index_path)
    return web.Response(text="index.html not found", status=404)


# === App Setup ===

def create_app() -> web.Application:
    app = web.Application()

    # Static
    app.router.add_get("/", handle_index)

    # Health
    app.router.add_get("/api/health", handle_health)

    # TTS
    app.router.add_get("/api/tts", handle_tts)
    app.router.add_get("/api/voices", handle_voices)

    # Text API
    app.router.add_get("/api/catalog", handle_catalog)
    app.router.add_get("/api/chapters", handle_chapters)
    app.router.add_get("/api/text", handle_text)

    # CORS
    app.router.add_route("OPTIONS", "/api/{path:.*}", handle_options)

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          Classical Chinese Reader - Server                   ║
╠══════════════════════════════════════════════════════════════╣
║  Open in browser:  http://localhost:{port:<24}║
║                                                              ║
║  Endpoints:                                                  ║
║    /              - Main application                         ║
║    /api/health    - Health check                             ║
║    /api/tts       - Text-to-speech                           ║
║    /api/catalog   - List available texts                     ║
║    /api/chapters  - Get chapters for a text                  ║
║    /api/text      - Get text content                         ║
║                                                              ║
║  Translations:    {str(TRANSLATIONS_DIR.absolute()):<41}║
╚══════════════════════════════════════════════════════════════╝
""")
    web.run_app(create_app(), port=port, print=None)
