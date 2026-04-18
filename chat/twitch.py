"""
Twitch 聊天室 IRC 監聽器。

透過 Twitch IRC over WebSocket 接收聊天室訊息，
每則訊息送到本地 FastAPI /event（chat 事件），由 Kunomi 回應。

設定（config/settings.yaml）：
  twitch:
    username:      Bot 的 Twitch 帳號名稱
    token:         OAuth token（格式：oauth:xxxxxxx）
    channel:       要監聽的頻道名稱（不含 #）
    response_rate: 0.3   # 每則訊息有 30% 機率回應（避免洗頻）
    min_interval:  8     # 兩次回應最少間隔秒數
"""
import asyncio
import logging
import random
import time
import httpx
import websockets
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_TW = _config.get("twitch", {})
_API_PORT = _config["api"]["port"]
_API_KEY = _config.get("api", {}).get("api_key", "")
_HEADERS = {"X-API-Key": _API_KEY} if _API_KEY else {}

_TWITCH_IRC = "wss://irc-ws.chat.twitch.tv:443"
_last_response: float = 0.0


async def _send_to_kunomi(username: str, message: str):
    global _last_response

    # 先嘗試計票（不影響後續回應邏輯）
    try:
        from tools.vote import tally
        tally(username, message)
    except Exception:
        pass

    rate = _TW.get("response_rate", 0.3)
    interval = _TW.get("min_interval", 8)

    if time.monotonic() - _last_response < interval:
        return
    if random.random() > rate:
        return

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"http://127.0.0.1:{_API_PORT}/event",
                json={"event_type": "chat", "context": {"username": username, "message": message}},
                headers=_HEADERS,
            )
            resp.raise_for_status()
        _last_response = time.monotonic()
        logger.info("Twitch [%s]: %s → %s", username, message[:40], resp.json().get("response", "")[:40])
    except Exception as e:
        logger.warning("送出 Twitch 訊息失敗：%s", e)


async def _connect():
    username = _TW.get("username", "")
    token = _TW.get("token", "")
    channel = _TW.get("channel", "").lower()

    if not all([username, token, channel]):
        logger.error("Twitch 設定不完整，請填入 username / token / channel")
        return

    logger.info("連接 Twitch IRC：#%s", channel)

    async with websockets.connect(_TWITCH_IRC) as ws:
        await ws.send(f"PASS {token}")
        await ws.send(f"NICK {username}")
        await ws.send(f"JOIN #{channel}")

        async for raw in ws:
            # 回應 PING 保持連線
            if raw.startswith("PING"):
                await ws.send("PONG :tmi.twitch.tv")
                continue

            # 解析 PRIVMSG
            # :username!username@username.tmi.twitch.tv PRIVMSG #channel :message
            if "PRIVMSG" not in raw:
                continue
            try:
                user = raw.split("!")[0].lstrip(":")
                msg = raw.split("PRIVMSG", 1)[1].split(":", 1)[1].strip()
                await _send_to_kunomi(user, msg)
            except IndexError:
                continue


async def start():
    """持續重連的 Twitch 監聽迴圈，斷線後 10 秒重試。"""
    while True:
        try:
            await _connect()
        except Exception as e:
            logger.warning("Twitch IRC 斷線（%s），10 秒後重試...", e)
        await asyncio.sleep(10)
