"""
Minecraft Forge 1.20.1 伺服器日誌監聽器。
在 4070 PC 上以獨立執行緒運行，偵測特定事件後呼叫 PC Agent /game-event。
"""
import re
import time
import logging
import threading
import httpx
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_MC_CFG = _config.get("minecraft", {})
_LOG_PATH = Path(_MC_CFG.get("log_path", ""))
_INTERVAL = _MC_CFG.get("poll_interval_seconds", 3)
_PC_HOST = f"http://127.0.0.1:8100"  # 本機 PC Agent
_PC_KEY = _config.get("pc_agent", {}).get("api_key", "")
_WEBHOOK_SECRET = _config.get("roblox", {}).get("webhook_secret", "")

# 事件規則：(正則, event_type, context_builder)
_RULES: list[tuple[re.Pattern, str, callable]] = [
    (
        re.compile(r"\[Server thread/INFO\].*?(\w+) was slain|(\w+) died|(\w+) fell"),
        "death",
        lambda m: {"bug_description": f"玩家 {m.group(1) or m.group(2) or m.group(3)} 死亡"},
    ),
    (
        re.compile(r"\[Server thread/INFO\].*?(\w+) has made the advancement \[(.+?)\]"),
        "win",
        lambda m: {"context_note": f"{m.group(1)} 解鎖成就：{m.group(2)}"},
    ),
    (
        re.compile(r"Exception|ERROR|Caused by", re.IGNORECASE),
        "bug",
        lambda m: {"bug_description": "伺服器發生異常，可能是 mod 衝突"},
    ),
]


def _notify(event_type: str, context: dict):
    secret = _config.get("roblox", {}).get("webhook_secret", "")
    try:
        httpx.post(
            f"{_PC_HOST}/game-event",
            json={"source": "minecraft", "event_type": event_type, "context": context, "secret": secret},
            headers={"X-API-Key": _PC_KEY} if _PC_KEY else {},
            timeout=10,
        )
    except Exception as e:
        logger.warning("推送 Minecraft 事件失敗：%s", e)


def _watch():
    if not _LOG_PATH or not _LOG_PATH.exists():
        logger.error("Minecraft 日誌路徑不存在：%s", _LOG_PATH)
        return

    logger.info("開始監聽 Minecraft 日誌：%s（間隔 %ds）", _LOG_PATH, _INTERVAL)
    last_size = _LOG_PATH.stat().st_size

    while True:
        time.sleep(_INTERVAL)
        try:
            current_size = _LOG_PATH.stat().st_size
            if current_size <= last_size:
                last_size = current_size  # 日誌輪替重置
                continue

            # 唯讀模式讀取新增內容
            with _LOG_PATH.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(last_size)
                new_lines = f.read()
            last_size = current_size

            for line in new_lines.splitlines():
                for pattern, event_type, ctx_fn in _RULES:
                    m = pattern.search(line)
                    if m:
                        _notify(event_type, ctx_fn(m))
                        break  # 一行只觸發第一個符合的規則

        except Exception as e:
            logger.warning("讀取日誌錯誤（將繼續監聽）：%s", e)


def start():
    """在背景執行緒啟動日誌監聽，不阻塞主程式。"""
    t = threading.Thread(target=_watch, daemon=True, name="mc-log-watcher")
    t.start()
    return t
