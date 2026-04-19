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
_vts_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _vts_lock
    if _vts_lock is None:
        _vts_lock = asyncio.Lock()
    return _vts_lock


def _inject_request(param_names: list, param_values: list, face_found: bool = True) -> dict:
    """Build InjectParameterDataRequest with faceFound=True to override VTS idle animation."""
    return {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": "kunomi-inject",
        "messageType": "InjectParameterDataRequest",
        "data": {
            "faceFound": face_found,
            "mode": "set",
            "parameterValues": [
                {"id": n, "value": float(v), "weight": 1.0}
                for n, v in zip(param_names, param_values)
            ],
        },
    }


async def vts_request(req: dict) -> dict:
    """Thread-safe wrapper: serialize all VTS WebSocket calls."""
    async with _get_lock():
        vts = await _get_vts()
        return await vts.request(req)


_inject_logged = False

async def vts_inject(param_names: list, param_values: list) -> dict:
    """Inject parameters with faceFound=True — overrides VTS idle animation."""
    global _inject_logged
    async with _get_lock():
        vts = await _get_vts()
        resp = await vts.request(_inject_request(param_names, param_values))
        if not _inject_logged:
            logger.info("vts_inject first response: %s", resp)
            _inject_logged = True
        return resp


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



async def _hold_params(param_names: list, param_values: list):
    """Continuously reinject parameters every 50 ms until cancelled (next emotion replaces this)."""
    try:
        while True:
            try:
                await vts_inject(param_names, param_values)
            except Exception:
                pass
            await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        pass


async def set_emotion(emotion: str) -> dict:
    """Inject Live2D parameter preset, hold until next emotion replaces it."""
    global _emotion_task

    preset = _PARAMS.get(emotion)
    if not preset:
        return {"status": "skipped", "reason": f"unknown emotion: {emotion}"}

    params_dict = preset.get("params", {})
    if not params_dict:
        return {"status": "skipped", "reason": "no params defined"}

    if _emotion_task and not _emotion_task.done():
        _emotion_task.cancel()

    param_names = list(params_dict.keys())
    param_values = [float(v) for v in params_dict.values()]
    _emotion_task = asyncio.create_task(_hold_params(param_names, param_values))

    logger.info("Live2D emotion: %s (持續)", emotion)
    return {"emotion": emotion}


async def _cancel_expression_after(hotkey_id: str, delay: float):
    await asyncio.sleep(delay)
    try:
        vts = await _get_vts()
        req = vts.vts_request.requestTriggerHotKey(hotkey_id)
        await vts_request(req)
        logger.debug("VTS hotkey deactivated: %s", hotkey_id)
    except Exception as e:
        logger.debug("VTS hotkey deactivate failed: %s", e)


async def set_expression(name: str, duration_seconds: float = 2.0) -> dict:
    """Trigger a VTube Studio expression via hotkey, auto-cancel after duration_seconds."""
    hotkey_id = _EXPR_MAP.get(name)
    if not hotkey_id:
        return {"status": "skipped", "reason": f"unknown expression: {name}"}

    try:
        vts = await _get_vts()
        req = vts.vts_request.requestTriggerHotKey(hotkey_id)
        await vts_request(req)
        logger.info("VTS hotkey triggered: %s (%s)", name, hotkey_id)
    except Exception as e:
        logger.warning("VTS hotkey failed (VTS not running?): %s", e)
        return {"status": "skipped", "reason": str(e)}

    if duration_seconds > 0:
        asyncio.create_task(_cancel_expression_after(hotkey_id, duration_seconds))

    return {"expression": name, "hotkey_id": hotkey_id, "duration": duration_seconds}
