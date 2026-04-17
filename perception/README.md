# perception/

遊戲環境感知模組，負責將遊戲內發生的事件傳遞給 Kunomi。

## 架構說明

```
遊戲端                        PC Agent（4070 PC）              M4 Mac
─────────────────────────────────────────────────────────────────────
Roblox Luau HttpService  →   POST /game-event            →   POST /event
Minecraft server log     →   perception/minecraft.py     →   POST /event
（polling，每 3 秒）           （背景執行緒監聽）
```

## 模組說明

### `minecraft.py`

監聽 Minecraft Forge 1.20.1 伺服器日誌（`latest.log`）。

- 唯讀模式開啟，僅讀取新增內容（記錄 file offset）
- 每 `minecraft.poll_interval_seconds` 秒掃描一次（預設 3 秒）
- 以背景執行緒運行，不阻塞 PC Agent 主服務

**偵測的事件：**

| 日誌關鍵字 | 觸發事件 |
|-----------|---------|
| `was slain` / `died` / `fell` | `death` |
| `has made the advancement` | `win` |
| `Exception` / `ERROR` / `Caused by` | `bug` |

**啟動方式（在 pc_agent/main.py 中加入）：**

```python
from perception.minecraft import start as start_mc
start_mc()
```

---

### `roblox.py`

不含執行邏輯，僅提供 **Roblox Luau 腳本範本**，說明如何從遊戲端發送 Webhook 到 PC Agent。

實際接收由 `pc_agent/server.py` 的 `POST /game-event` 端點處理。

**Roblox 端設定步驟：**
1. 在 Roblox Studio → Game Settings → Security 啟用 `Allow HTTP Requests`
2. 將 `perception/roblox.py` 中的 Luau 範本貼入 ServerScript
3. 替換 `YOUR_PC_IP` 與 `YOUR_WEBHOOK_SECRET`

---

## 待辦事項

- [x] Minecraft 日誌監聽器（唯讀、間隔輪詢、背景執行緒）
- [x] Roblox Webhook Luau 範本
- [ ] 在 `pc_agent/main.py` 加入 `start_mc()` 呼叫（設定好 `minecraft.log_path` 後）
- [ ] 填入 `config/settings.yaml` 的 `minecraft.log_path`
- [ ] 填入 `config/settings.yaml` 的 `roblox.webhook_secret`
- [ ] 新增 CODM / Delta Force 事件來源（未來擴充）
