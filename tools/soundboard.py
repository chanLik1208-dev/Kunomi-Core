import logging
import httpx
import yaml
from pathlib import Path
from tools import register_tool

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_PC = _config.get("pc_agent", {}).get("host", "http://localhost:8100")
_KEY = _config.get("pc_agent", {}).get("api_key", "")
_HEADERS = {"X-API-Key": _KEY} if _KEY else {}


@register_tool("soundboard")
async def play_sound(name: str) -> dict:
    """
    觸發 4070 PC 播放音效。
    name 對應 config/soundboard.yaml 的 key（death / win / explosion 等）。
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{_PC}/soundboard/{name}", headers=_HEADERS)
            resp.raise_for_status()
        logger.info("soundboard: %s", name)
        return resp.json()
    except httpx.ConnectError:
        logger.warning("soundboard: PC Agent not reachable, skipping %s", name)
        return {"status": "skipped", "reason": "PC Agent offline"}
    except Exception as e:
        logger.warning("soundboard: %s failed: %s", name, e)
        return {"status": "error", "reason": str(e)}
