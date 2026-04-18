# core/

系統神經中樞，負責 LLM 通訊、Prompt 組裝、內容過濾。運行於 M4 Mac。

## 模組說明

### `prompt.py`

定義 Kunomi 的人設（System Prompt）與各情境模板。啟動時自動從 ChromaDB 讀取過去直播總結注入 System Prompt。

**支援事件類型：**

| event_type | 觸發情境 | 必要 context 欄位 |
|------------|---------|----------------|
| `death` | 玩家死亡 | 無 |
| `win` | 遊戲勝利 | 無 |
| `bug` | 遊戲 Bug | `bug_description` |
| `chat` | 觀眾留言 | `username`, `message` |
| `idle` | 冷場自言自語 | `seconds` |
| `voice` | 語音指令 | `command` |
| `vision` | 截圖吐槽 | `screen_desc` |

```python
from core.prompt import build_prompt

prompt = build_prompt("chat", {"username": "Ray", "message": "你好可愛"})
```

---

### `llm.py`

非同步 Ollama HTTP 客戶端，對接 M4 Mac 本機的 Ollama。

```python
await chat(prompt="...", system="...")
await chat_with_event("death")
await chat_with_event("chat", {"username": "Ray", "message": "讚讚"})
```

---

### `filter.py`

雙層過濾器：規則過濾（關鍵詞黑名單）+ AI 語意過濾（LLM 判斷惡意引導）。

```python
from core.filter import rule_filter, semantic_filter, sanitize_response

if not rule_filter(user_message):       # 第一層：關鍵詞
    raise HTTPException(400)
if not await semantic_filter(message):  # 第二層：語意
    raise HTTPException(400)

clean = sanitize_response(llm_output)   # 清理 LLM 輸出
```

---

## 資料流

```
事件觸發
  → build_prompt()          （組裝含人設 + 記憶的 prompt）
  → chat_with_event()       （呼叫 Ollama）
  → sanitize_response()     （清理輸出）
  → speak() / API 回傳
```

## 待辦事項

- [x] System Prompt 基本人設（冷血毒舌貓耳少女 Kunomi）
- [x] 所有事件類型 prompt 模板
- [x] 啟動時注入過去直播總結到 System Prompt
- [x] 雙層過濾器（規則 + AI 語意）
- [x] `sanitize_response()` 清理括號動作描述
- [x] Ollama 連線失敗重試（最多 2 次）
- [ ] 調整 System Prompt 語氣（依實際測試結果微調）
- [ ] 支援 streaming 模式（逐字輸出給 TTS，減少首字延遲）
- [ ] `blocked_keywords.txt` 熱更新（目前需重啟才生效）
- [ ] 加入回應快取（短時間內相同事件不重複呼叫 LLM）
