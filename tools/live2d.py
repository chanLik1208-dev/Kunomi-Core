"""
VTube Studio Live2D 參數注入工具。

直接控制 Live2D 模型的頭部、眼神、眉毛、嘴角等參數，
比表情切換更細膩，可做到低頭斜眼、側頭傾聽等細節動作。

使用方式：
  1. 自動觸發：chat_with_event() 回應後根據 event_type 自動套用
  2. 工具呼叫：LLM 輸出 {"tool": "live2d_emotion", "args": {"emotion": "sarcastic"}}
  3. 手動呼叫：await set_emotion("surprised")
"""
import asyncio
import logging
import yaml
from pathlib import Path
from tools import register_tool

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_VTS_CFG = _config.get("vtube_studio", {})

_PARAMS: dict = yaml.safe_load(
    Path("config/live2d_params.yaml").read_text(encoding="utf-8")
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
        raise RuntimeError("pyvts 未安裝，請執行 pip install pyvts")

    plugin_info = {
        "plugin_name": _VTS_CFG.get("plugin_name", "Kunomi-core"),
        "developer": _VTS_CFG.get("plugin_developer", "dev"),
    }
    vts = pyvts.vts(plugin_info=plugin_info, vts_api_info={"port": 8001})
    await vts.connect()
    await vts.request_authenticate_token()
    await vts.request_authenticate()
    _vts_client = vts
    logger.info("VTube Studio 已連線（Live2D 參數模式）")
    return vts


async def _inject(params: dict[str, float]):
    """向 VTube Studio 注入一組參數值。"""
    vts = await _get_vts()
    parameter_list = [
        {"id": k, "value": float(v), "weight": 1.0}
        for k, v in params.items()
    ]
    req = vts.vts_request.InjectParameterDataRequest(
        id="kunomi-live2d",
        parameter_values=parameter_list,
    )
    await vts.request(req)


async def _restore_to_neutral(delay: float):
    """等待 delay 秒後恢復 neutral 情緒。"""
    await asyncio.sleep(delay)
    neutral = _PARAMS.get("neutral", {}).get("params", {})
    if neutral:
        try:
            await _inject(neutral)
        except Exception as e:
            logger.warning("恢復 neutral 失敗：%s", e)


@register_tool("live2d_emotion")
async def set_emotion(emotion: str) -> dict:
    """
    套用情緒對應的 Live2D 參數預設值。
    emotion 對應 config/live2d_params.yaml 的 key。
    """
    global _restore_task

    preset = _PARAMS.get(emotion)
    if not preset:
        raise ValueError(f"未知情緒：{emotion}，請檢查 config/live2d_params.yaml")

    params = preset.get("params", {})
    duration = preset.get("duration", 3)

    try:
        await _inject(params)
        logger.info("Live2D 情緒：%s（%s 秒）", emotion, duration)
    except Exception as e:
        logger.warning("Live2D 參數注入失敗（VTube Studio 未啟動？）：%s", e)
        return {"status": "skipped", "reason": str(e)}

    # 取消上一個恢復任務，重新排程
    if _restore_task and not _restore_task.done():
        _restore_task.cancel()

    if duration > 0:
        _restore_task = asyncio.create_task(_restore_to_neutral(duration))

    return {"emotion": emotion, "params_count": len(params), "duration": duration}


# event_type → 情緒映射（自動觸發用）
_EVENT_EMOTION: dict[str, str] = {
    "death":   "death",
    "win":     "win",
    "bug":     "surprised",
    "chat":    "sarcastic",
    "idle":    "idle",
    "voice":   "voice",
    "vision":  "vision",
}


async def auto_emotion(event_type: str):
    """根據 event_type 自動套用對應情緒，用於 chat_with_event() 回應後呼叫。"""
    emotion = _EVENT_EMOTION.get(event_type, "sarcastic")
    try:
        await set_emotion(emotion)
    except Exception as e:
        logger.debug("auto_emotion 略過（%s）：%s", emotion, e)
