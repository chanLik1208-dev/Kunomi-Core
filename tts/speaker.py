"""
GPT-SoVITS TTS 模組（M4 Mac）。

說話流程：
  1. 設 asr.listener.is_speaking = True（暫停 ASR 錄音，防回音）
  2. 呼叫 GPT-SoVITS API 取得音訊
  3. 播放音訊（sounddevice）
  4. 播放結束後設 is_speaking = False（恢復 ASR 監聽）
"""
import io
import logging
import threading
import httpx
import sounddevice as sd
import numpy as np
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_TTS_URL: str = _config.get("tts", {}).get("api_url", "http://127.0.0.1:9880")
_SAMPLE_RATE = 32000  # GPT-SoVITS 預設輸出取樣率


def _set_speaking(value: bool):
    try:
        import asr.listener as asr
        asr.is_speaking = value
    except Exception:
        pass  # ASR 未啟動時靜默略過


async def speak(text: str) -> bool:
    """
    合成並播放語音，阻塞至播放完畢。
    回傳 True 表示成功，False 表示 TTS 服務不可用（靜默略過）。
    """
    if not text.strip():
        return True

    _set_speaking(True)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                _TTS_URL,
                params={"text": text, "text_language": "zh"},
            )
            resp.raise_for_status()

        audio_bytes = resp.content
        _play_blocking(audio_bytes)
        return True

    except httpx.ConnectError:
        logger.warning("TTS 服務未啟動（%s），跳過語音合成", _TTS_URL)
        return False
    except Exception as e:
        logger.error("TTS 合成失敗：%s", e)
        return False
    finally:
        _set_speaking(False)


def _play_blocking(audio_bytes: bytes):
    """將 GPT-SoVITS 回傳的 WAV bytes 解碼並播放，阻塞至結束。"""
    import wave

    with wave.open(io.BytesIO(audio_bytes)) as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())

    audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if n_channels > 1:
        audio_np = audio_np.reshape(-1, n_channels)

    done = threading.Event()

    def _callback(outdata, frames, time_info, status):
        nonlocal audio_np
        chunk = audio_np[:frames]
        if len(chunk) < frames:
            outdata[: len(chunk)] = chunk.reshape(-1, 1) if audio_np.ndim == 1 else chunk
            outdata[len(chunk) :] = 0
            raise sd.CallbackStop()
        outdata[:] = chunk.reshape(-1, 1) if audio_np.ndim == 1 else chunk
        audio_np = audio_np[frames:]

    with sd.OutputStream(
        samplerate=sample_rate,
        channels=1 if audio_np.ndim == 1 else n_channels,
        dtype="float32",
        callback=_callback,
        finished_callback=done.set,
    ):
        done.wait()
