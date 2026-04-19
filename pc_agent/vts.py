"""
VTube Studio control module for PC Agent.
Runs on Windows PC where VTube Studio is localhost.

pyvts API used:
- requestSetMultiParameterValue(parameters, values) — Live2D param injection
- requestTriggerHotKey(hotkeyID) — expression activation via VTS hotkey
"""
import asyncio
import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_VTS_CFG = _config.get("vtube_studio", {})


def _parse_port() -> int:
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
_emotion_task: asyncio.Task | None = None


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
        "authentication_token_path": "vts_token.txt",
    }
    vts = pyvts.vts(plugin_info=plugin_info, vts_api_info={"name": "VTubeStudioPublicAPI", "version": "1.0", "port": _PORT})
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



async def _hold_params(param_names: list, param_values: list, duration: float):
    """Continuously reinject parameters every 50 ms for `duration` seconds, then restore neutral."""
    try:
        deadline = asyncio.get_event_loop().time() + duration
        while asyncio.get_event_loop().time() < deadline:
            try:
                vts = await _get_vts()
                req = vts.vts_request.requestSetMultiParameterValue(param_names, param_values)
                await vts.request(req)
            except Exception:
                pass
            await asyncio.sleep(0.05)
    finally:
        neutral = _PARAMS.get("neutral", {}).get("params", {})
        if neutral:
            try:
                vts = await _get_vts()
                req = vts.vts_request.requestSetMultiParameterValue(
                    list(neutral.keys()), [float(v) for v in neutral.values()]
                )
                await vts.request(req)
            except Exception as e:
                logger.debug("restore neutral failed: %s", e)


async def set_emotion(emotion: str) -> dict:
    """Inject Live2D parameter preset for the given emotion."""
    global _emotion_task

    preset = _PARAMS.get(emotion)
    if not preset:
        return {"status": "skipped", "reason": f"unknown emotion: {emotion}"}

    params_dict = preset.get("params", {})
    duration = preset.get("duration", 3)

    if not params_dict:
        return {"status": "skipped", "reason": "no params defined"}

    if _emotion_task and not _emotion_task.done():
        _emotion_task.cancel()

    param_names = list(params_dict.keys())
    param_values = [float(v) for v in params_dict.values()]

    if duration > 0:
        _emotion_task = asyncio.create_task(_hold_params(param_names, param_values, duration))
    else:
        try:
            vts = await _get_vts()
            req = vts.vts_request.requestSetMultiParameterValue(param_names, param_values)
            await vts.request(req)
        except Exception as e:
            logger.warning("Live2D inject failed (VTS not running?): %s", e)
            return {"status": "skipped", "reason": str(e)}

    logger.info("Live2D emotion: %s (%ds)", emotion, duration)
    return {"emotion": emotion, "duration": duration}


async def set_expression(name: str, duration_seconds: float = 2.0) -> dict:
    """Trigger a VTube Studio expression via hotkey."""
    hotkey_id = _EXPR_MAP.get(name)
    if not hotkey_id:
        return {"status": "skipped", "reason": f"unknown expression: {name}"}

    try:
        vts = await _get_vts()
        req = vts.vts_request.requestTriggerHotKey(hotkey_id)
        await vts.request(req)
        logger.info("VTS hotkey triggered: %s (%s)", name, hotkey_id)
    except Exception as e:
        logger.warning("VTS hotkey failed (VTS not running?): %s", e)
        return {"status": "skipped", "reason": str(e)}

    return {"expression": name, "hotkey_id": hotkey_id, "duration": duration_seconds}
