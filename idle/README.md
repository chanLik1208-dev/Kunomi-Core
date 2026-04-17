# idle/

冷場偵測與自言自語迴圈，讓 Kunomi 在無活動時主動製造節目效果。

## 運作邏輯

```
任何活動（聊天/事件）→ activity_ping() → 計時器歸零
                                              ↓
                              每 5 秒檢查距上次活動時間
                                              ↓
                         超過 idle_timeout_seconds？
                          否 → 繼續等待
                          是 → 已達 idle_max_loops？
                                否 → 觸發 idle 事件 → Kunomi 自言自語 → 等 15 秒 → 繼續
                                是 → 靜待新活動
```

## 設定

在 `config/settings.yaml` 的 `character` 區段調整：

| 欄位 | 說明 | 預設值 |
|------|------|--------|
| `idle_timeout_seconds` | 冷場幾秒後觸發自言自語 | `120` |
| `idle_max_loops` | 連續自言自語最多幾輪 | `5` |

**建議值：**  
- 直播中設 `120`（2 分鐘），避免太快打斷遊戲中的沉默  
- 測試時設 `15`，方便驗證觸發

## API

```python
from idle.state import activity_ping, set_enabled, start

start()               # 啟動監控（FastAPI startup 時呼叫）
activity_ping()       # 重置計時器（任何活躍事件發生時呼叫）
set_enabled(False)    # 停用自言自語（例：截圖分析期間）
set_enabled(True)     # 重新啟用
```

## Discord 指令整合

`!idle on/off` 指令呼叫 `set_enabled()`，透過 `discord_bot/commands/admin.py` 實作。

## 待辦事項

- [x] 冷場計時器與 activity_ping() 機制
- [x] 自言自語迴圈上限（idle_max_loops）
- [x] FastAPI startup 自動啟動
- [x] /event 與 /chat 端點接收時自動呼叫 activity_ping()
- [x] idle 事件本身不重置計時器（避免自言自語互相觸發）
- [x] `set_enabled()` 接入 Discord Bot `!idle` 指令（`discord_bot/commands/admin.py`）
- [ ] 自言自語話題池（`config/idle_topics.yaml`），注入到 idle prompt context
