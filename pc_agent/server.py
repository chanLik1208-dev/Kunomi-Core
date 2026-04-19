import logging
import httpx
import yaml
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_API_KEY: str = _config.get("pc_agent", {}).get("api_key", "")
_MAC_API: str = _config.get("api", {}).get(
    "mac_host", f"http://127.0.0.1:{_config['api']['port']}"
)
_VISION_MODEL: str = _config.get("vision", {}).get("model", "llava:7b")
_LLM_HOST: str = _config["llm"]["host"]

app = FastAPI(title="Kunomi PC Agent")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pc_agent"}


@app.on_event("startup")
async def on_startup():
    if _config.get("asr", {}).get("push_to_talk_key"):
        from pc_agent.asr import start as start_asr
        start_asr()
        logger.info("ASR 按鍵發話已啟動")

    if _config.get("vtube_studio", {}).get("api_url") or _config.get("vtube_studio", {}).get("port"):
        try:
            from pc_agent.idle_motion import start as start_idle
            from pc_agent.vts import _get_vts
            start_idle(_get_vts)
            logger.info("Idle motion loop 已啟動")
        except Exception as e:
            logger.warning("Idle motion 啟動失敗（VTS 未連線？）: %s", e)


async def verify_key(request: Request):
    if not _API_KEY:
        return
    if request.headers.get("X-API-Key", "") != _API_KEY:
        raise HTTPException(status_code=401, detail="無效的 API Key")


@app.exception_handler(Exception)
async def error_handler(_req: Request, exc: Exception):
    logger.exception("PC Agent 錯誤：%s", exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ── 截圖 ──────────────────────────────────────────────────────────────────────

@app.post("/screenshot", dependencies=[Depends(verify_key)])
async def screenshot():
    """截圖並送 Vision 模型分析，回傳畫面描述與 AI 吐槽。"""
    from pc_agent.screenshot import capture_base64

    b64, saved_path = capture_base64()

    # 呼叫 Ollama Vision 模型（llava）
    payload = {
        "model": _VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": "這是一張遊戲截圖，請用一句話描述你看到的主要內容。只描述事實，不要加評論。",
            "images": [b64],
        }],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{_LLM_HOST}/api/chat", json=payload)
        resp.raise_for_status()
        screen_desc = resp.json()["message"]["content"].strip()

    # 把描述送回 M4 Mac 的 FastAPI 觸發 vision 事件
    mac_key = _config.get("api", {}).get("api_key", "")
    headers = {"X-API-Key": mac_key} if mac_key else {}
    async with httpx.AsyncClient(timeout=30) as client:
        mac_resp = await client.post(
            f"{_MAC_API}/event",
            json={"event_type": "vision", "context": {"screen_desc": screen_desc}},
            headers=headers,
        )
        mac_resp.raise_for_status()
        ai_response = mac_resp.json()["response"]

    return {
        "screen_desc": screen_desc,
        "ai_response": ai_response,
        "saved_path": saved_path,
    }


# ── TTS 播放 ──────────────────────────────────────────────────────────────────

@app.post("/tts/play", dependencies=[Depends(verify_key)])
async def tts_play(request: Request):
    """Receive audio bytes (WAV or MP3) from Mac and play locally via pygame."""
    import asyncio
    import os
    import tempfile
    import pygame
    import pc_agent.asr as asr_mod

    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="empty audio body")

    # detect format by magic bytes
    suffix = ".wav" if audio_bytes[:4] == b"RIFF" else ".mp3"

    # pre-compute amplitude envelope for lip sync (WAV only)
    amp_frames: list[float] = []
    if suffix == ".wav":
        try:
            import io as _io
            import wave
            import struct
            with wave.open(_io.BytesIO(audio_bytes)) as wf:
                sw = wf.getsampwidth()
                fr = wf.getframerate()
                chunk_frames = int(fr * 0.05)  # 50ms
                fmt = {1: "b", 2: "h", 4: "i"}.get(sw, "h")
                max_val = float(2 ** (8 * sw - 1))
                while True:
                    raw = wf.readframes(chunk_frames)
                    if not raw:
                        break
                    n = len(raw) // sw
                    samples = struct.unpack(f"{n}{fmt}", raw)
                    rms = (sum(s * s for s in samples) / max(n, 1)) ** 0.5
                    amp_frames.append(min(rms / max_val * 3.0, 1.0))  # boost gain
        except Exception:
            amp_frames = []

    asr_mod.is_speaking = True
    tmp_path = None
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100)

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()

        # push subtitle before playback
        from urllib.parse import unquote
        subtitle_text = unquote(request.headers.get("X-Subtitle-Text", ""))
        if subtitle_text:
            from pc_agent.subtitle import broadcast
            asyncio.create_task(broadcast(subtitle_text))

        # lip sync: drive mouth via idle_motion
        try:
            from pc_agent.idle_motion import set_mouth
            _has_lipsync = True
        except Exception:
            _has_lipsync = False

        frame_idx = 0
        while pygame.mixer.music.get_busy():
            if _has_lipsync:
                if amp_frames:
                    set_mouth(amp_frames[min(frame_idx, len(amp_frames) - 1)])
                    frame_idx += 1
                else:
                    # MP3 fallback: talking sine wave
                    import math as _math
                    import time as _time
                    set_mouth(max(0.0, _math.sin(_time.monotonic() * _math.pi * 8) * 0.6))
            await asyncio.sleep(0.05)

        if _has_lipsync:
            set_mouth(None)
        pygame.mixer.music.unload()
    finally:
        asr_mod.is_speaking = False
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    logger.info("TTS played (%d bytes, %s)", len(audio_bytes), suffix)
    return {"status": "played", "bytes": len(audio_bytes)}


# ── 字幕 ──────────────────────────────────────────────────────────────────────

@app.get("/subtitle", response_class=HTMLResponse, include_in_schema=False)
async def subtitle_page():
    from pc_agent.subtitle import _HTML
    return HTMLResponse(content=_HTML)


@app.websocket("/subtitle/ws")
async def subtitle_ws(websocket: WebSocket):
    from pc_agent.subtitle import connect, disconnect
    await connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        disconnect(websocket)


# ── VTube Studio ─────────────────────────────────────────────────────────────

class VtsEmotionRequest(BaseModel):
    emotion: str

class VtsExpressionRequest(BaseModel):
    name: str
    duration_seconds: float = 2.0


@app.post("/vts/emotion", dependencies=[Depends(verify_key)])
async def vts_emotion(req: VtsEmotionRequest):
    """Set Live2D emotion via parameter injection (VTS runs locally on PC)."""
    from pc_agent.vts import set_emotion
    return await set_emotion(req.emotion)


@app.post("/vts/expression", dependencies=[Depends(verify_key)])
async def vts_expression(req: VtsExpressionRequest):
    """Trigger a VTube Studio expression."""
    from pc_agent.vts import set_expression
    return await set_expression(req.name, req.duration_seconds)


# ── 音效板 ────────────────────────────────────────────────────────────────────

@app.post("/soundboard/{name}", dependencies=[Depends(verify_key)])
async def play_sound(name: str):
    """播放指定音效。name 對應 config/soundboard.yaml 的 key。"""
    try:
        from pc_agent.soundboard import play
        path = play(name)
        return {"status": "played", "sound": name, "file": path}
    except (ValueError, FileNotFoundError) as e:
        logger.warning("soundboard: %s", e)
        return {"status": "skipped", "sound": name, "reason": str(e)}


# ── 遊戲事件 Webhook（Roblox / Minecraft 透過此端點推送事件）──────────────────

class GameEvent(BaseModel):
    source: str          # "roblox" | "minecraft"
    event_type: str      # death / win / bug / custom
    context: dict = {}
    secret: str = ""


@app.post("/game-event")
async def game_event(req: GameEvent):
    """接收遊戲內事件，轉發給 M4 Mac FastAPI。"""
    expected_secret = _config.get("roblox", {}).get("webhook_secret", "")
    if expected_secret and req.secret != expected_secret:
        raise HTTPException(status_code=401, detail="Webhook secret 不符")

    logger.info("收到遊戲事件 [%s / %s]", req.source, req.event_type)

    mac_key = _config.get("api", {}).get("api_key", "")
    headers = {"X-API-Key": mac_key} if mac_key else {}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_MAC_API}/event",
            json={"event_type": req.event_type, "context": req.context},
            headers=headers,
        )
        resp.raise_for_status()

    return {"status": "forwarded", "response": resp.json().get("response")}
