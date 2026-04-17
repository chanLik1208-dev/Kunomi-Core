# discord_bot/

Discord Bot 遙控器，讓你在手機或其他裝置遠端控制直播系統。

## 定位

Discord Bot **不是**聊天室互動入口，而是**開發者遙控器**：

- 遠端觸發事件（例如手機下指令讓 AI 吐槽）
- 接收系統重要通知（錯誤警報、溫度過高）
- 查詢系統狀態

> ⚠️ 聊天室互動（Twitch / YouTube 彈幕）走獨立模組，不經過 Discord Bot，避免速率限制。

---

## 計劃指令

| 指令 | 說明 |
|------|------|
| `!health` | 查詢系統健康狀態 |
| `!event <type>` | 手動觸發事件（例：`!event death`） |
| `!chat <訊息>` | 讓 Kunomi 回應一則訊息 |
| `!idle on/off` | 開關自言自語模式 |
| `!screenshot` | 觸發截圖吐槽 |
| `!shutdown` | 安全關閉系統 |

---

## 實作說明（第二階段）

Bot 透過 HTTP 呼叫本地 FastAPI，不直接操作 LLM：

```
Discord 指令 → discord.py Bot → POST http://localhost:8000/event → FastAPI → Ollama
```

這樣架構的好處：
- Bot 崩潰不影響直播系統
- 所有邏輯集中在 FastAPI，Bot 只是薄薄的介面層

---

## 速率限制注意

- Discord Bot 每秒訊息上限：5 則
- **禁止**將遊戲日誌、聊天室串流直接發到 Discord
- 系統通知加入節流機制，同類事件 30 秒內只發一次

---

## 檔案規劃

```
discord_bot/
├── README.md       本文件
├── bot.py          Bot 主程式（第二階段建立）
└── commands/       各指令模組（第二階段建立）
```

## 待辦事項

### 第二階段 ✅

- [ ] 建立 Discord Application 並取得 Bot Token，填入 `config/settings.yaml`
- [x] 建立 `discord_bot/bot.py`，初始化 `discord.py` Client
- [x] 實作 `!health` 指令
- [x] 實作 `!event <type>` 指令（支援所有事件類型）
- [x] 實作 `!chat <訊息>` 指令
- [x] 實作 `!idle on/off` 指令（開關自言自語模式）
- [ ] 實作 `!screenshot` 指令（第三階段端點建好後啟用）
- [x] 實作 `!shutdown` 指令（15 秒內需回覆 `!confirm` 才執行）
- [x] 加入節流機制：同類系統通知 30 秒內只推一則

### 安全 ✅

- [x] 限制指令只有 `allowed_user_ids` 清單內的使用者可執行
- [x] `!shutdown` 指令加二次確認
- [x] Bot Token 不得 commit 進 git，`.gitignore` 已排除 `settings.yaml`，範本存於 `settings.example.yaml`
