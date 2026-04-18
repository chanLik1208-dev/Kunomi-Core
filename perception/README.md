# perception/

遊戲環境感知模組，負責將遊戲內事件傳遞給 Kunomi。運行於 Windows PC。

## 架構

```
遊戲端                        PC（pc_agent）                    Mac
─────────────────────────────────────────────────────────────────────
Roblox Luau HttpService  →   POST /game-event             →   POST /event
Minecraft server log     →   perception/minecraft.py      →   POST /event
（polling，每 3 秒）           （背景執行緒）
```

## 模組說明

### `minecraft.py`

監聽 Minecraft Forge 1.20.1 伺服器日誌（`latest.log`），唯讀輪詢。

**偵測的事件：**

| 日誌關鍵字 | 觸發事件 |
|-----------|---------|
| `was slain` / `died` / `fell` | `death` |
| `has made the advancement` | `win` |
| `Exception` / `ERROR` / `Caused by` | `bug` |

啟動（在 `pc_agent/main.py`）：
```python
from perception.minecraft import start as start_mc
if config.get("minecraft", {}).get("log_path"):
    start_mc()
```

---

### `roblox.py`

提供 Roblox Luau 腳本範本，說明如何從遊戲端發 Webhook 到 pc_agent。  
實際接收由 `pc_agent/server.py` 的 `POST /game-event` 處理。

**設定步驟：**
1. Roblox Studio → Game Settings → Security → 啟用 Allow HTTP Requests
2. 貼入 `perception/roblox.py` 的 Luau 範本到 ServerScript
3. 替換 `YOUR_PC_IP` 與 `YOUR_WEBHOOK_SECRET`

---

## 待辦事項

- [x] Minecraft 日誌監聽器（唯讀、間隔輪詢、背景執行緒）
- [x] Roblox Webhook Luau 範本
- [ ] 填入 `config/settings.yaml` 的 `minecraft.log_path`
- [ ] 填入 `config/settings.yaml` 的 `roblox.webhook_secret`
- [ ] 在 `pc_agent/main.py` 加入 `start_mc()` 呼叫
- [ ] 新增其他遊戲事件來源（CODM / Delta Force 等未來擴充）
