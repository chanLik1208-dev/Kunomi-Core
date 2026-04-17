"""
Idle State 冷場偵測與自言自語迴圈。

任何模組呼叫 activity_ping() 即可重置冷場計時器（收到觀眾訊息、遊戲事件等）。
超過 idle_timeout_seconds 無活動時，自動觸發 idle 事件，最多執行 idle_max_loops 輪。
"""
import asyncio
import logging
import time
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_CHAR_CFG = _config.get("character", {})
_TIMEOUT: int = _CHAR_CFG.get("idle_timeout_seconds", 120)
_MAX_LOOPS: int = _CHAR_CFG.get("idle_max_loops", 5)
_API_PORT: int = _config["api"]["port"]
_API_KEY: str = _config.get("api", {}).get("api_key", "")

_last_activity: float = time.monotonic()
_idle_loop_count: int = 0
_task: asyncio.Task | None = None
_enabled: bool = True


def activity_ping():
    """重置冷場計時器，應在任何活躍事件發生時呼叫。"""
    global _last_activity, _idle_loop_count
    _last_activity = time.monotonic()
    _idle_loop_count = 0
    logger.debug("activity_ping：計時器重置")


def set_enabled(value: bool):
    global _enabled
    _enabled = value
    logger.info("Idle State：%s", "啟用" if value else "停用")


async def _trigger_idle(elapsed: int):
    import httpx
    headers = {"X-API-Key": _API_KEY} if _API_KEY else {}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"http://127.0.0.1:{_API_PORT}/event",
                json={"event_type": "idle", "context": {"seconds": elapsed}},
                headers=headers,
            )
            resp.raise_for_status()
            logger.info("自言自語觸發（第 %d 輪）：%s",
                        _idle_loop_count, resp.json().get("response", "")[:60])
    except Exception as e:
        logger.warning("觸發 idle 事件失敗：%s", e)


async def _watch():
    global _idle_loop_count
    while True:
        await asyncio.sleep(5)

        if not _enabled:
            continue

        elapsed = int(time.monotonic() - _last_activity)
        if elapsed < _TIMEOUT:
            continue

        if _idle_loop_count >= _MAX_LOOPS:
            # 達到上限，等到有新活動才重置
            logger.debug("自言自語已達上限（%d 輪），等待新活動", _MAX_LOOPS)
            continue

        _idle_loop_count += 1
        await _trigger_idle(elapsed)

        # 每輪自言自語後短暫等待，避免立刻再觸發
        await asyncio.sleep(15)


def start():
    """在當前 asyncio event loop 啟動 Idle 監控 task。"""
    global _task
    if _task and not _task.done():
        return _task
    _task = asyncio.create_task(_watch())
    logger.info("Idle State 監控已啟動（逾時 %ds，上限 %d 輪）", _TIMEOUT, _MAX_LOOPS)
    return _task
