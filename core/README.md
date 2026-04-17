# core/

系統神經中樞，負責 LLM 通訊、Prompt 組裝、內容過濾。

## 模組說明

### `prompt.py`

定義 Kunomi 的人設（System Prompt）與各情境模板。

**支援事件類型：**

| event_type | 觸發情境 | 必要 context 欄位 |
|------------|---------|----------------|
| `death` | 玩家死亡 | 無 |
| `win` | 遊戲勝利 | 無 |
| `bug` | 遊戲 Bug | `bug_description` |
| `chat` | 觀眾留言 | `username`, `message` |
| `idle` | 冷場自言自語 | `seconds`（冷場秒數） |
| `voice` | 語音指令 | `command` |
| `vision` | 截圖吐槽 | `screen_desc` |

**使用範例：**
```python
from core.prompt import build_prompt

prompt = build_prompt("chat", {"username": "Ray", "message": "你好可愛"})
```

---

### `llm.py`

非同步 Ollama HTTP 客戶端，對接 RTX 4070 PC 上的本地 LLM。

**主要函數：**

```python
# 直接送 prompt
await chat(prompt="...", system="...")

# 事件快捷方式（自動組裝 prompt）
await chat_with_event("death")
await chat_with_event("chat", {"username": "Ray", "message": "讚讚"})
```

**注意：** `llm.host` 需填入 4070 PC 的局域網 IP，確保兩機在同一網段。

---

### `filter.py`

雙層過濾器的第一層（規則過濾）。

```python
from core.filter import rule_filter, sanitize_response

# 過濾輸入（True = 通過）
if not rule_filter(user_message):
    raise HTTPException(400, "訊息被封鎖")

# 清理 LLM 輸出
clean_text = sanitize_response(llm_output)
```

**第二層（AI 語意過濾）：** 預留於 `settings.yaml` 的 `filter.ai_semantic_filter` 旗標，第二階段實作。

---

## 資料流

```
事件觸發 → build_prompt() → chat_with_event() → Ollama LLM
                                                      ↓
                                            sanitize_response()
                                                      ↓
                                               回傳給 API / TTS
```

## 待辦事項

### `prompt.py`

- [ ] 調整 System Prompt 語氣，依實際測試結果微調
- [ ] 新增 `stream_start` / `stream_end` 情境模板（開播 / 收播時的台詞）
- [ ] 新增 `achievement` 情境模板（解鎖成就）
- [ ] 考慮加入動態話題注入（從 `idle_topics.yaml` 隨機抽取，第四階段）

### `llm.py`

- [x] 加入連線失敗重試機制（最多重試 2 次）
- [ ] 加入回應快取（短時間內相同事件不重複呼叫 LLM，節省資源）
- [ ] 支援 streaming 模式（逐字輸出給 TTS，減少首字延遲）
- [ ] 加入 token 使用量 logging，監控 VRAM 壓力

### `filter.py`

- [x] 實作 AI 語意過濾第二層（呼叫 LLM 判斷是否為惡意引導）
- [x] 擴充 `sanitize_response()`，清理括號動作描述、多餘空白行
- [ ] `blocked_keywords.txt` 熱更新（檔案變更時自動重新載入，不需重啟）
