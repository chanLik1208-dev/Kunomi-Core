# memory/

ChromaDB 長期記憶模組，讓 Kunomi 記得過去的直播。運行於 M4 Mac。

## Collections

| Collection | 內容 | 保留策略 |
|-----------|------|---------|
| `events` | 遊戲事件、有趣片段、失敗經驗 | 最多 `max_events` 筆，超過自動刪除最舊的 |
| `sessions` | 每次直播結束的今日總結 | 永久保留（依日期 ID，重播同日會覆蓋）|

## 資料流

```
遊戲事件發生
  → tools.memory_save(content, event_type)
  → save_event()  →  ChromaDB events

直播結束
  → POST /stream/end
  → 查詢今日 events → LLM 生成總結
  → save_session_summary()  →  ChromaDB sessions

下次啟動
  → core.prompt._build_system_prompt()
  → get_recent_summaries()
  → 注入 System Prompt「過去直播記憶」區段
```

## API

```python
from memory.store import save_event, query_events, save_session_summary, get_recent_summaries

save_event("death", "玩家在最後一秒被爆頭，血量剩 1", {"game": "CODM"})
results = query_events("玩家死亡的搞笑瞬間", n_results=5)
save_session_summary("今天最印象深刻的是被同一個位置狙了三次。", "2026-04-18")
summaries = get_recent_summaries(n=3)
```

## 設定

`config/settings.yaml` 的 `memory` 區段：

| 欄位 | 說明 | 預設值 |
|------|------|--------|
| `db_path` | ChromaDB 本地資料夾 | `chroma_db` |
| `max_events` | 事件記憶上限 | `500` |

## 注意事項

- ChromaDB 首次建立 collection 時會下載 embedding 模型（約 70MB），需要網路
- `chroma_db/` 已加入 `.gitignore`，不會上傳
- 記憶模組失效不影響主功能（`core/prompt.py` 的記憶注入已包 try/except）

## 待辦事項

- [x] ChromaDB PersistentClient 連線
- [x] `save_event` / `query_events`（events collection）
- [x] `save_session_summary` / `get_recent_summaries`（sessions collection）
- [x] 記憶上限自動清理（`max_events`）
- [x] 啟動時自動注入過去總結到 System Prompt
- [x] `POST /stream/end` 直播結束總結端點
- [x] `GET /memory/recent` / `GET /memory/summaries` 查詢端點
- [ ] 查詢結果在 LLM 回應前自動注入 context（目前需手動呼叫 `memory_query` 工具）
- [ ] 定期備份 `chroma_db/` 到外部儲存
