"""
TTS 模組（M4 Mac）。

優先使用 GPT-SoVITS（config tts.api_url 有設定時）；
否則 fallback 到 edge-tts（免安裝雲端合成，zh-TW 女聲）。

合成後 POST WAV bytes 到 Windows pc_agent /tts/play 播放（OBS 可擷取）。
"""
import io
import logging
import httpx
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_tts_cfg   = _config.get("tts", {})
_TTS_URL: str = _tts_cfg.get("api_url", "")          # 空字串 = 不用 GPT-SoVITS
_VOICE: str   = _tts_cfg.get("edge_voice", "zh-TW-HsiaoChenNeural")
_PC_AGENT: str   = _config.get("pc_agent", {}).get("host", "http://127.0.0.1:8100")
_PC_API_KEY: str = _config.get("pc_agent", {}).get("api_key", "")


async def _synthesize_edge(text: str) -> bytes:
    """edge-tts 合成，回傳 MP3 bytes（pc_agent sounddevice 可播放）。"""
    import edge_tts
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, _VOICE)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


async def _synthesize_gptsovits(text: str) -> bytes:
    """GPT-SoVITS 合成，回傳 WAV bytes。"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(_TTS_URL, params={"text": text, "text_language": "zh"})
        resp.raise_for_status()
    return resp.content


async def _post_to_pc(audio_bytes: bytes, content_type: str) -> None:
    """POST 音訊到 Windows pc_agent /tts/play，阻塞至播放完畢。"""
    headers: dict = {"Content-Type": content_type}
    if _PC_API_KEY:
        headers["X-API-Key"] = _PC_API_KEY
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{_PC_AGENT}/tts/play", content=audio_bytes, headers=headers)
        resp.raise_for_status()


async def speak(text: str) -> bool:
    """
    合成語音並送到 Windows pc_agent 播放。
    回傳 True 表示成功，False 表示服務不可用（靜默略過）。
    """
    if not text.strip():
        return True

    try:
        if _TTS_URL:
            try:
                audio = await _synthesize_gptsovits(text)
                ctype = "audio/wav"
                logger.debug("TTS: GPT-SoVITS")
            except Exception as e:
                logger.warning("TTS: GPT-SoVITS failed (%s), falling back to edge-tts", e)
                audio = await _synthesize_edge(text)
                ctype = "audio/mpeg"
        else:
            audio = await _synthesize_edge(text)
            ctype = "audio/mpeg"
            logger.debug("TTS: edge-tts voice=%s", _VOICE)

        await _post_to_pc(audio, ctype)
        logger.info("TTS done: %s", text[:50])
        return True

    except httpx.ConnectError as e:
        logger.warning("TTS/PC Agent connection failed (%s), skipping", e)
        return False
    except Exception as e:
        logger.error("TTS failed: %s", e)
        return False
