"""
GPT-SoVITS TTS 模組（M4 Mac）。

說話流程：
  1. 設 asr.listener.is_speaking = True（暫停 ASR 錄音，防回音）
  2. 呼叫 GPT-SoVITS API 取得音訊 bytes
  3. POST 音訊到 Windows pc_agent /tts/play → 由 PC 本地播放（OBS 可擷取）
  4. 播放結束後設 is_speaking = False（恢復 ASR 監聽）
"""
import logging
import httpx
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_TTS_URL: str = _config.get("tts", {}).get("api_url", "http://127.0.0.1:9880")
_PC_AGENT: str = _config.get("pc_agent", {}).get("host", "http://127.0.0.1:8100")
_PC_API_KEY: str = _config.get("pc_agent", {}).get("api_key", "")


def _set_speaking(value: bool):
    try:
        import asr.listener as asr
        asr.is_speaking = value
    except Exception:
        pass


async def speak(text: str) -> bool:
    """
    合成語音並送到 Windows pc_agent 播放，阻塞至 pc_agent 回應（播放完畢）。
    回傳 True 表示成功，False 表示服務不可用（靜默略過）。
    """
    if not text.strip():
        return True

    _set_speaking(True)
    try:
        # 1. 向 GPT-SoVITS 取得音訊 bytes
        async with httpx.AsyncClient(timeout=30) as client:
            tts_resp = await client.get(
                _TTS_URL,
                params={"text": text, "text_language": "zh"},
            )
            tts_resp.raise_for_status()

        audio_bytes = tts_resp.content

        # 2. POST 音訊到 Windows pc_agent 播放
        headers = {"X-API-Key": _PC_API_KEY} if _PC_API_KEY else {}
        async with httpx.AsyncClient(timeout=60) as client:
            play_resp = await client.post(
                f"{_PC_AGENT}/tts/play",
                content=audio_bytes,
                headers={**headers, "Content-Type": "audio/wav"},
            )
            play_resp.raise_for_status()

        logger.info("TTS 播放完畢：%s", text[:40])
        return True

    except httpx.ConnectError as e:
        logger.warning("TTS 或 PC Agent 連線失敗（%s），跳過語音合成", e)
        return False
    except Exception as e:
        logger.error("TTS 合成/播放失敗：%s", e)
        return False
    finally:
        _set_speaking(False)
