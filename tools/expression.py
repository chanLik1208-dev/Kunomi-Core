"""
VTube Studio expression tool — delegates to PC Agent /vts/expression.
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


@register_tool("expression")
async def trigger_expression(name: str, duration_seconds: float = 2.0) -> dict:
    """Trigger a VTube Studio expression via PC Agent."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{_PC_AGENT}/vts/expression",
                json={"name": name, "duration_seconds": duration_seconds},
                headers=_HEADERS,
            )
            resp.raise_for_status()
        result = resp.json()
        logger.info("VTS expression: %s → %s", name, result.get("status"))
        return result
    except httpx.ConnectError:
        logger.debug("Expression: PC Agent offline, skipping %s", name)
        return {"status": "skipped", "reason": "PC Agent offline"}
    except Exception as e:
        logger.warning("VTS expression failed: %s", e)
        return {"status": "skipped", "reason": str(e)}
