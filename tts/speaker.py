"""
TTS 模組（M4 Mac）。

優先使用 GPT-SoVITS（config tts.api_url 有設定時）；
否則 fallback 到 edge-tts。

合成後 POST 音訊到 Windows pc_agent /tts/play 播放（OBS 可擷取）。
播放結束後等待 1-3 秒再處理下一句（佇列序列化）。
"""
import asyncio
import io
import logging
import random
import httpx
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_tts_cfg     = _config.get("tts", {})
_TTS_URL: str  = _tts_cfg.get("api_url", "")
_VOICE: str    = _tts_cfg.get("edge_voice", "zh-TW-HsiaoChenNeural")
_PC_AGENT: str   = _config.get("pc_agent", {}).get("host", "http://127.0.0.1:8100")
_PC_API_KEY: str = _config.get("pc_agent", {}).get("api_key", "")

# ── TTS 佇列（序列化播放）────────────────────────────────────────────────────
_queue: asyncio.Queue = asyncio.Queue()
_worker_started = False


async def _worker():
    """背景工作者：依序取出文字、合成、播放、等待間隔。"""
    while True:
        text = await _queue.get()
        try:
            await _synthesize_and_play(text)
            # 播完後等待 1-3 秒
            delay = random.uniform(1.0, 3.0)
            await asyncio.sleep(delay)
        except Exception as e:
            logger.error("TTS worker error: %s", e)
        finally:
            _queue.task_done()


def _ensure_worker():
    global _worker_started
    if not _worker_started:
        asyncio.create_task(_worker())
        _worker_started = True


# ── 合成 ──────────────────────────────────────────────────────────────────────

async def _synthesize_edge(text: str) -> bytes:
    import edge_tts
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, _VOICE)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


async def _synthesize_gptsovits(text: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(_TTS_URL, params={"text": text, "text_language": "zh"})
        resp.raise_for_status()
    return resp.content


async def _synthesize_and_play(text: str) -> None:
    """合成語音並阻塞等待 PC Agent 播放完畢。"""
    if _TTS_URL:
        try:
            audio = await _synthesize_gptsovits(text)
            ctype = "audio/wav"
        except Exception as e:
            logger.warning("GPT-SoVITS failed (%s), falling back to edge-tts", e)
            audio = await _synthesize_edge(text)
            ctype = "audio/mpeg"
    else:
        audio = await _synthesize_edge(text)
        ctype = "audio/mpeg"

    headers: dict = {"Content-Type": ctype, "X-Subtitle-Text": text}
    if _PC_API_KEY:
        headers["X-API-Key"] = _PC_API_KEY

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{_PC_AGENT}/tts/play", content=audio, headers=headers)
        resp.raise_for_status()

    logger.info("TTS done: %s", text[:50])


# ── 公開 API ──────────────────────────────────────────────────────────────────

async def speak(text: str) -> bool:
    """
    將文字加入 TTS 佇列，立即回傳（非阻塞）。
    背景工作者依序播放，播完等 1-3 秒再播下一句。
    """
    if not text.strip():
        return True
    try:
        _ensure_worker()
        await _queue.put(text)
        return True
    except httpx.ConnectError as e:
        logger.warning("TTS/PC Agent connection failed (%s), skipping", e)
        return False
    except Exception as e:
        logger.error("TTS enqueue failed: %s", e)
        return False
