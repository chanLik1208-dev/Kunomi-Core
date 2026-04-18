# idle/

冷場偵測與自言自語迴圈，讓 Kunomi 在無活動時主動製造節目效果。運行於 M4 Mac。

## 運作邏輯

```
任何活動（聊天 / 遊戲事件）
  → activity_ping()          （計時器歸零）

背景執行緒每 5 秒檢查：
  距上次活動 < idle_timeout_seconds？
    → 繼續等待
  已超時且 loop_count < idle_max_loops？
    → 觸發 /event idle → Kunomi 自言自語 → loop_count++
    → 等 15 秒後繼續
  已達 idle_max_loops？
    → 靜待新活動（loop_count 重置）
```

**idle 事件本身不重置計時器**，避免 Kunomi 自言自語互相觸發無限迴圈。

## 設定

`config/settings.yaml` 的 `character` 區段：

| 欄位 | 說明 | 預設值 |
|------|------|--------|
| `idle_timeout_seconds` | 冷場幾秒後觸發 | `120` |
| `idle_max_loops` | 連續自言自語最多幾輪 | `5` |

建議值：直播中 `120`，測試時改 `15`。

## API

```python
from idle.state import activity_ping, set_enabled, start

start()               # FastAPI startup 時呼叫
activity_ping()       # 有活躍事件時呼叫（/event、/chat 已自動呼叫）
set_enabled(False)    # 暫停自言自語
set_enabled(True)     # 恢復
```

## 待辦事項

- [x] 冷場計時器與 `activity_ping()` 機制
- [x] 自言自語迴圈上限（`idle_max_loops`）
- [x] FastAPI startup 自動啟動
- [x] idle 事件本身不重置計時器
- [x] `set_enabled()` 接入 Discord Bot `!idle` 指令
- [ ] 自言自語話題池（`config/idle_topics.yaml`）隨機注入 context
