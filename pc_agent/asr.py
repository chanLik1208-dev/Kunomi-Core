"""
Faster-Whisper STT 模組（Windows PC）。

按住 push_to_talk_key（預設 alt）錄音，放開後辨識，
結果透過 HTTP 送到 M4 Mac 的 FastAPI /event（voice 事件）。

回音防護：is_speaking flag 由 /tts/play 端點控制，
TTS 播放期間不錄音，避免 AI 錄到自己聲音。
"""
import logging
import threading
import httpx
import numpy as np
import sounddevice as sd
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_ASR_CFG = _config.get("asr", {})
_PTT_KEY = _ASR_CFG.get("push_to_talk_key", "alt").lower()
_MODEL_SIZE = _ASR_CFG.get("model_size", "medium")
_LANGUAGE = _ASR_CFG.get("language", "zh")
_SAMPLE_RATE = 16000
_MAC_API = _config.get("api", {}).get(
    "mac_host", f"http://127.0.0.1:{_config['api']['port']}"
)
_MAC_KEY = _config.get("api", {}).get("api_key", "")

# TTS 播放中旗標（由 pc_agent/server.py 的 /tts/play 端點設定）
is_speaking: bool = False

_stop_event = threading.Event()
_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    from faster_whisper import WhisperModel
    logger.info("載入 Faster-Whisper 模型：%s（CUDA）", _MODEL_SIZE)
    _model = WhisperModel(_MODEL_SIZE, device="auto", compute_type="int8")
    return _model


def _transcribe(audio_bytes: bytes) -> str:
    model = _load_model()
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _ = model.transcribe(audio_np, language=_LANGUAGE, beam_size=5)
    return "".join(seg.text for seg in segments).strip()


def _send_voice_command(text: str):
    if not text:
        return
    logger.info("語音指令：%s", text)
    headers = {"X-API-Key": _MAC_KEY} if _MAC_KEY else {}
    try:
        httpx.post(
            f"{_MAC_API}/event",
            json={"event_type": "voice", "context": {"command": text}},
            headers=headers,
            timeout=30,
        )
    except Exception as e:
        logger.warning("送出語音指令失敗：%s", e)


def _ptt_loop():
    try:
        from pynput import keyboard
    except ImportError:
        logger.error("pynput 未安裝，請執行 pip install pynput")
        return

    logger.info("ASR 按鍵發話已啟動，按住 %s 鍵錄音", _PTT_KEY.upper())
    recording: list = []
    stream: sd.InputStream | None = None

    def _start_recording():
        nonlocal stream, recording
        if is_speaking:
            logger.debug("TTS 播放中，跳過錄音")
            return
        recording = []
        stream = sd.InputStream(samplerate=_SAMPLE_RATE, channels=1, dtype="int16")
        stream.start()

    def _stop_recording():
        nonlocal stream
        if stream is None:
            return
        stream.stop()
        avail = stream.read_available
        data, _ = stream.read(avail) if avail > 0 else (stream.read(1)[0][:0], False)
        stream.close()
        stream = None

        audio_bytes = data.tobytes()
        if len(audio_bytes) < _SAMPLE_RATE * 2 * 0.3:
            return

        text = _transcribe(audio_bytes)
        if text:
            _send_voice_command(text)

    _PTT_MAP = {
        "alt":   {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r},
        "ctrl":  {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r},
        "shift": {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r},
    }
    ptt_keys = _PTT_MAP.get(_PTT_KEY, _PTT_MAP["alt"])

    def on_press(key):
        if key in ptt_keys and stream is None:
            _start_recording()

    def on_release(key):
        if key in ptt_keys:
            _stop_recording()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        _stop_event.wait()
        listener.stop()


def start() -> threading.Thread:
    _stop_event.clear()
    t = threading.Thread(target=_ptt_loop, daemon=True, name="asr-ptt")
    t.start()
    return t


def stop():
    _stop_event.set()
