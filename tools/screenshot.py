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


@register_tool("screenshot")
async def screenshot() -> dict:
    """
    觸發 4070 PC 截圖，送 Vision 模型分析並讓 Kunomi 吐槽。
    回傳 screen_desc（畫面描述）與 ai_response（Kunomi 吐槽）。
    """
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(f"{_PC}/screenshot", headers=_HEADERS)
        resp.raise_for_status()

    data = resp.json()
    logger.info("截圖吐槽：%s", data.get("ai_response", "")[:60])
    return data
