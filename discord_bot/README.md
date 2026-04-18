# discord_bot/

Discord Bot 遙控器，讓你在手機或其他裝置遠端控制直播系統。運行於 M4 Mac。

## 定位

Discord Bot 是**開發者遙控器**，不是觀眾互動入口：

- 遠端觸發事件（手機下指令讓 AI 吐槽）
- 接收系統通知（錯誤警報）
- 查詢系統狀態

觀眾互動（Twitch / YouTube 彈幕）走 `chat/` 模組，不經 Discord Bot。

## 指令一覽

| 指令 | 說明 |
|------|------|
| `!health` | 查詢系統健康狀態 |
| `!event <type>` | 手動觸發事件（`!event death`）|
| `!chat <訊息>` | 讓 Kunomi 回應一則訊息 |
| `!idle on/off` | 開關自言自語模式 |
| `!screenshot` | 觸發截圖吐槽 |
| `!shutdown` | 安全關閉系統（需 `!confirm` 二次確認）|

## 架構

```
Discord 指令
  → discord.py Bot（Mac）
  → POST http://localhost:8000/event
  → FastAPI → LLM → TTS → PC 播放
```

## 安全設計

- `allowed_user_ids` 限制只有特定使用者可執行指令
- `!shutdown` 需在 15 秒內回覆 `!confirm`
- Bot Token 不得 commit 進 git（`settings.yaml` 已排除）

## 節流機制

同類系統通知 30 秒內只推一則，避免事件爆炸時洗頻 Discord。

## 待辦事項

- [x] `bot.py`：discord.py Client 初始化
- [x] `!health`、`!event`、`!chat`、`!idle`、`!shutdown` 指令
- [x] 節流機制（`notify_throttle_seconds`）
- [x] `allowed_user_ids` 白名單驗證
- [x] `!shutdown` 二次確認
- [ ] 填入 `config/settings.yaml` 的 `discord.token` 與 `discord.notify_channel_id`
- [ ] 填入 `discord.allowed_user_ids`（你的 Discord 使用者 ID）
