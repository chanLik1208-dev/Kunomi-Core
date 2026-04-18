import asyncio
import logging
import yaml
from pathlib import Path
from tools import register_tool

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_VTS_CFG = _config.get("vtube_studio", {})
_EXPR_MAP: dict[str, str] = yaml.safe_load(
    Path("config/expressions.yaml").read_text(encoding="utf-8")
)

# pyvts 客戶端（懶加載，避免沒裝時影響其他模組）
_vts_client = None


async def _get_vts():
    global _vts_client
    if _vts_client is not None:
        return _vts_client
    try:
        import pyvts
    except ImportError:
        raise RuntimeError("pyvts 未安裝，請執行 pip install pyvts")

    plugin_info = {
        "name": _VTS_CFG.get("plugin_name", "Kunomi-core"),
        "developer": _VTS_CFG.get("plugin_developer", "dev"),
    }
    vts = pyvts.vts(plugin_info=plugin_info, vts_api_info={"port": 8001})
    try:
        await vts.connect()
        await vts.request_authenticate_token()
        await vts.request_authenticate()
    except Exception:
        _vts_client = None
        raise
    _vts_client = vts
    return vts


@register_tool("expression")
async def trigger_expression(name: str, duration_seconds: float = 2.0) -> dict:
    """
    觸發 VTube Studio 表情，持續 duration_seconds 秒後恢復預設。
    name 對應 config/expressions.yaml 的 key（surprised / happy 等）。
    """
    expr_id = _EXPR_MAP.get(name)
    if not expr_id:
        raise ValueError(f"未知表情：{name}，請檢查 config/expressions.yaml")

    vts = await _get_vts()

    # 啟用表情
    req = vts.vts_request.requestSetExpressionState(expr_id, active=True)
    await vts.request(req)
    logger.info("表情觸發：%s (%s)", name, expr_id)

    # 計時後關閉
    async def _deactivate():
        await asyncio.sleep(duration_seconds)
        req_off = vts.vts_request.requestSetExpressionState(expr_id, active=False)
        await vts.request(req_off)

    asyncio.create_task(_deactivate())
    return {"expression": name, "vts_id": expr_id, "duration": duration_seconds}
