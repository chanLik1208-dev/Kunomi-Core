"""
Live2D emotion tool — delegates to PC Agent /vts/emotion.
VTube Studio runs on Windows PC, so pyvts control must run there too.
"""
import logging
import httpx
import yaml
from pathlib import Path
from tools import register_tool

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_PC_AGENT: str = _config.get("pc_agent", {}).get("host", "http://127.0.0.1:8100")
_PC_API_KEY: str = _config.get("pc_agent", {}).get("api_key", "")
_HEADERS: dict = {"X-API-Key": _PC_API_KEY} if _PC_API_KEY else {}

_EVENT_EMOTION: dict[str, str] = {
    "death":  "death",
    "win":    "win",
    "bug":    "surprised",
    "chat":   "sarcastic",
    "idle":   "idle",
    "voice":  "voice",
    "vision": "vision",
}


@register_tool("live2d_emotion")
async def set_emotion(emotion: str) -> dict:
    """Set Live2D emotion via PC Agent (VTube Studio is on Windows PC)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{_PC_AGENT}/vts/emotion",
                json={"emotion": emotion},
                headers=_HEADERS,
            )
            resp.raise_for_status()
        result = resp.json()
        logger.info("Live2D emotion: %s → %s", emotion, result.get("status"))
        return result
    except httpx.ConnectError:
        logger.debug("Live2D: PC Agent offline, skipping emotion %s", emotion)
        return {"status": "skipped", "reason": "PC Agent offline"}
    except Exception as e:
        logger.warning("Live2D emotion failed: %s", e)
        return {"status": "skipped", "reason": str(e)}


async def auto_emotion(event_type: str) -> None:
    """Automatically apply emotion after an event response."""
    emotion = _EVENT_EMOTION.get(event_type, "sarcastic")
    await set_emotion(emotion)
