import logging
import httpx
import yaml
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
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
    """接收 Mac 傳來的 WAV bytes，在 Windows 本地播放（OBS 可擷取）。阻塞至播放完畢。"""
    import io
    import threading
    import wave
    import numpy as np
    import sounddevice as sd

    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="empty audio body")

    with wave.open(io.BytesIO(audio_bytes)) as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())

    audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if n_channels > 1:
        audio_np = audio_np.reshape(-1, n_channels)

    done = threading.Event()

    def _callback(outdata, frames, _time, _status):
        nonlocal audio_np
        chunk = audio_np[:frames]
        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk.reshape(-1, 1) if audio_np.ndim == 1 else chunk
            outdata[len(chunk):] = 0
            raise sd.CallbackStop()
        outdata[:] = chunk.reshape(-1, 1) if audio_np.ndim == 1 else chunk
        audio_np = audio_np[frames:]

    with sd.OutputStream(
        samplerate=sample_rate,
        channels=n_channels,
        dtype="float32",
        callback=_callback,
        finished_callback=done.set,
    ):
        done.wait()

    logger.info("TTS 播放完畢（%d bytes）", len(audio_bytes))
    return {"status": "played", "bytes": len(audio_bytes)}


# ── 音效板 ────────────────────────────────────────────────────────────────────

@app.post("/soundboard/{name}", dependencies=[Depends(verify_key)])
async def play_sound(name: str):
    """播放指定音效。name 對應 config/soundboard.yaml 的 key。"""
    from pc_agent.soundboard import play
    path = play(name)
    return {"status": "played", "sound": name, "file": path}


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
