"""
YouTube Live 聊天室輪詢模組。

YouTube Data API v3 不提供 WebSocket，需定期輪詢 liveChatMessages。
每次取得新訊息後送到本地 FastAPI /event（chat 事件）。

設定（config/settings.yaml）：
  youtube:
    api_key:         Google Cloud API Key（需啟用 YouTube Data API v3）
    live_chat_id:    直播的 liveChatId（每次開播不同，需動態取得或手動填入）
    poll_interval:   5      # 輪詢間隔秒數（建議 >= 5，避免超出配額）
    response_rate:   0.3    # 每則訊息有 30% 機率回應
    min_interval:    8      # 兩次回應最少間隔秒數

liveChatId 取得方式：
  GET https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails&id=VIDEO_ID&key=API_KEY
  回應中的 liveStreamingDetails.activeLiveChatId
"""
import asyncio
import logging
import random
import time
import httpx
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_YT = _config.get("youtube", {})
_API_PORT = _config["api"]["port"]
_API_KEY_KUNOMI = _config.get("api", {}).get("api_key", "")
_HEADERS = {"X-API-Key": _API_KEY_KUNOMI} if _API_KEY_KUNOMI else {}

_YT_API = "https://www.googleapis.com/youtube/v3"
_last_response: float = 0.0


async def _get_live_chat_id(video_id: str, yt_api_key: str) -> str | None:
    """從 video_id 動態取得 liveChatId。"""
    url = f"{_YT_API}/videos"
    params = {"part": "liveStreamingDetails", "id": video_id, "key": yt_api_key}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        return None
    return items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")


async def _send_to_kunomi(username: str, message: str):
    global _last_response

    try:
        from tools.vote import tally
        tally(username, message)
    except Exception:
        pass

    rate = _YT.get("response_rate", 0.3)
    interval = _YT.get("min_interval", 8)

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
        logger.info("YouTube [%s]: %s → %s", username, message[:40], resp.json().get("response", "")[:40])
    except Exception as e:
        logger.warning("送出 YouTube 訊息失敗：%s", e)


async def _poll(live_chat_id: str, yt_api_key: str):
    """持續輪詢 liveChatMessages，回傳時已處理所有新訊息。"""
    page_token: str | None = None
    interval = max(_YT.get("poll_interval", 5), 5)

    url = f"{_YT_API}/liveChat/messages"

    while True:
        params = {
            "liveChatId": live_chat_id,
            "part": "snippet,authorDetails",
            "key": yt_api_key,
            "maxResults": 200,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                username = item["authorDetails"]["displayName"]
                message = item["snippet"].get("displayMessage", "")
                if message:
                    await _send_to_kunomi(username, message)

            page_token = data.get("nextPageToken")
            # API 建議的輪詢間隔（毫秒）
            suggested_ms = data.get("pollingIntervalMillis", interval * 1000)
            await asyncio.sleep(max(suggested_ms / 1000, interval))

        except Exception as e:
            logger.warning("YouTube 輪詢錯誤（%s），%d 秒後重試...", e, interval)
            await asyncio.sleep(interval)


async def start():
    """啟動 YouTube 聊天室監聽，自動處理 liveChatId 取得與重連。"""
    yt_api_key = _YT.get("api_key", "")
    live_chat_id = _YT.get("live_chat_id", "")
    video_id = _YT.get("video_id", "")

    if not yt_api_key:
        logger.error("youtube.api_key 未設定，跳過 YouTube 聊天室監聽")
        return

    # 動態取得 liveChatId
    if not live_chat_id and video_id:
        logger.info("從 video_id 取得 liveChatId...")
        try:
            live_chat_id = await _get_live_chat_id(video_id, yt_api_key)
            logger.info("liveChatId：%s", live_chat_id)
        except Exception as e:
            logger.error("取得 liveChatId 失敗：%s", e)
            return

    if not live_chat_id:
        logger.error("youtube.live_chat_id 未設定且無法自動取得，跳過")
        return

    logger.info("開始監聽 YouTube 聊天室（liveChatId：%s）", live_chat_id)
    while True:
        try:
            await _poll(live_chat_id, yt_api_key)
        except Exception as e:
            logger.warning("YouTube 監聽中斷（%s），10 秒後重試...", e)
            await asyncio.sleep(10)
