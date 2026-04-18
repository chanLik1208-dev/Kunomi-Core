# chat/

聊天室整合模組。監聽直播平台的觀眾留言，轉發給 Kunomi 回應。

## 模組一覽

| 檔案 | 平台 | 協定 |
|------|------|------|
| `twitch.py` | Twitch | IRC over WebSocket (`wss://irc-ws.chat.twitch.tv:443`) |
| `youtube.py` | YouTube Live | HTTP 輪詢（YouTube Data API v3） |

---

## Twitch 設定

```yaml
# config/settings.yaml
twitch:
  username: "your_bot_account"
  token: "oauth:xxxxxxxxxxxxxxxxxxxxxxx"  # https://twitchapps.com/tmi/
  channel: "your_channel_name"           # 不含 #
  response_rate: 0.3
  min_interval: 8
```

啟動後自動重連，斷線 10 秒後重試。

---

## YouTube Live 設定

```yaml
# config/settings.yaml
youtube:
  api_key: "AIza..."          # Google Cloud Console 取得，需啟用 YouTube Data API v3
  video_id: "dQw4w9WgXcQ"    # 直播影片 ID（liveChatId 自動取得）
  live_chat_id: ""            # 或直接填入 liveChatId 跳過自動取得
  poll_interval: 5
  response_rate: 0.3
  min_interval: 8
```

`live_chat_id` 與 `video_id` 擇一填入即可。優先使用 `live_chat_id`，未填則從 `video_id` 動態取得。

---

## 投票整合

兩個模組都會在收到訊息時呼叫 `tools.vote.tally(username, message)`，
自動識別 `1` / `2` / `3` 格式的投票訊息並計票，不影響回應邏輯。

---

## 待辦事項

- [x] Twitch IRC WebSocket 監聽器（`twitch.py`）
- [x] YouTube Data API v3 輪詢器（`youtube.py`）
- [x] 投票計票 hook（`tally()` 整合）
- [x] `response_rate` / `min_interval` 節流防洗頻
- [x] `api/server.py` 啟動時自動偵測設定並建立非同步 Task
- [ ] 支援 Twitch Channel Points / Bits 事件（透過 EventSub）
- [ ] YouTube Super Chat / Super Sticker 事件辨識
- [ ] 多平台同時上線時的合併回應佇列（避免同秒兩條回應）
