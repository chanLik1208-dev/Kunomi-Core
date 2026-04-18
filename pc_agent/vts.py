"""
VTube Studio control module for PC Agent.
Runs on Windows PC where VTube Studio is localhost.
"""
import asyncio
import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_VTS_CFG = _config.get("vtube_studio", {})

def _parse_port() -> int:
    # support both vtube_studio.port and vtube_studio.api_url
    if "port" in _VTS_CFG:
        return int(_VTS_CFG["port"])
    url = _VTS_CFG.get("api_url", "")
    if url:
        try:
            return int(url.rstrip("/").rsplit(":", 1)[-1])
        except (ValueError, IndexError):
            pass
    return 8001

_PORT: int = _parse_port()

_PARAMS: dict = yaml.safe_load(
    Path("config/live2d_params.yaml").read_text(encoding="utf-8")
)
_EXPR_MAP: dict = yaml.safe_load(
    Path("config/expressions.yaml").read_text(encoding="utf-8")
)

_vts_client = None
_restore_task: asyncio.Task | None = None


async def _get_vts():
    global _vts_client
    if _vts_client is not None:
        return _vts_client
    try:
        import pyvts
    except ImportError:
        raise RuntimeError("pyvts not installed: pip install pyvts")

    plugin_info = {
        "plugin_name": _VTS_CFG.get("plugin_name", "Kunomi-core"),
        "developer":   _VTS_CFG.get("plugin_developer", "dev"),
        "authentication_token": "",
    }
    vts = pyvts.vts(plugin_info=plugin_info, vts_api_info={"port": _PORT})
    try:
        await vts.connect()
        await vts.request_authenticate_token()
        await vts.request_authenticate()
    except Exception:
        _vts_client = None
        raise
    _vts_client = vts
    logger.info("VTube Studio connected on port %d", _PORT)
    return vts


async def _restore_neutral(delay: float):
    await asyncio.sleep(delay)
    neutral = _PARAMS.get("neutral", {}).get("params", {})
    if not neutral:
        return
    try:
        vts = await _get_vts()
        param_list = [{"id": k, "value": float(v)} for k, v in neutral.items()]
        req = vts.vts_request.InjectParameterDataRequest(parameter_values=param_list)
        await vts.request(req)
    except Exception as e:
        logger.debug("restore neutral failed: %s", e)


async def set_emotion(emotion: str) -> dict:
    """Inject Live2D parameter preset for the given emotion."""
    global _restore_task

    preset = _PARAMS.get(emotion)
    if not preset:
        return {"status": "skipped", "reason": f"unknown emotion: {emotion}"}

    params = preset.get("params", {})
    duration = preset.get("duration", 3)

    try:
        vts = await _get_vts()
        param_list = [{"id": k, "value": float(v)} for k, v in params.items()]
        req = vts.vts_request.InjectParameterDataRequest(parameter_values=param_list)
        await vts.request(req)
        logger.info("Live2D emotion: %s (%ds)", emotion, duration)
    except Exception as e:
        logger.warning("Live2D inject failed (VTS not running?): %s", e)
        return {"status": "skipped", "reason": str(e)}

    if _restore_task and not _restore_task.done():
        _restore_task.cancel()
    if duration > 0:
        _restore_task = asyncio.create_task(_restore_neutral(duration))

    return {"emotion": emotion, "duration": duration}


async def set_expression(name: str, duration_seconds: float = 2.0) -> dict:
    """Activate a VTube Studio expression by name."""
    expr_id = _EXPR_MAP.get(name)
    if not expr_id:
        return {"status": "skipped", "reason": f"unknown expression: {name}"}

    try:
        vts = await _get_vts()
        req = vts.vts_request.requestSetExpressionState(expr_id, active=True)
        await vts.request(req)
        logger.info("VTS expression: %s (%s)", name, expr_id)

        async def _deactivate():
            await asyncio.sleep(duration_seconds)
            try:
                req_off = vts.vts_request.requestSetExpressionState(expr_id, active=False)
                await vts.request(req_off)
            except Exception:
                pass

        asyncio.create_task(_deactivate())
    except Exception as e:
        logger.warning("VTS expression failed (VTS not running?): %s", e)
        return {"status": "skipped", "reason": str(e)}

    return {"expression": name, "vts_id": expr_id, "duration": duration_seconds}
