# config/

系統所有設定檔與靜態資料集中於此，支援熱更新（修改後重啟服務生效）。

## 檔案說明

### `settings.yaml`

全域設定檔，各模組啟動時讀取。

| 區段 | 說明 | 執行機器 |
|------|------|---------|
| `llm` | Ollama 主機 IP、模型名稱、逾時秒數 | Mac（本機） |
| `tts` | GPT-SoVITS API 位址 | Mac |
| `asr` | Faster-Whisper 模型大小、按鍵發話設定 | Mac |
| `api` | FastAPI 監聽 host / port | Mac |
| `discord` | Bot Token、通知頻道 ID | Mac |
| `character` | 冷場逾時秒數、自言自語最大循環次數 | Mac |
| `filter` | 過濾詞庫路徑、是否啟用 AI 語意過濾 | Mac |
| `vtube_studio` | VTube Studio WebSocket 位址（PC） | Mac → PC |
| `pc_agent` | PC Agent 位址與 API Key | Mac → PC |
| `vision` | Ollama Vision 模型名稱 | PC |
| `soundboard` | 音效資料夾路徑 | PC |
| `minecraft` | 日誌路徑、輪詢間隔 | PC |
| `roblox` | Webhook secret | PC |
| `memory` | ChromaDB 路徑、事件上限 | Mac |
| `twitch` | Bot 帳號、OAuth token、頻道 | Mac |
| `youtube` | API Key、影片 ID、輪詢設定 | Mac |

**首次設定必填：**
```yaml
llm:
  host: "http://127.0.0.1:11434"     # Ollama 在 Mac 本機

tts:
  api_url: "http://127.0.0.1:9880"   # GPT-SoVITS 在 Mac 本機

pc_agent:
  host: "http://192.168.1.XXX:8100"  # PC 局域網 IP
  api_key: "your_secret"

vtube_studio:
  api_url: "ws://127.0.0.1:8001"     # VTube Studio 在 PC（本機）

discord:
  token: "your_bot_token_here"
  notify_channel_id: 123456789
```

---

### `settings.example.yaml`

`settings.yaml` 的範本，不含敏感資料，已 commit 進 git。

---

### `blocked_keywords.txt`

規則過濾詞庫，每行一個封鎖詞，`#` 開頭為注釋。

```
# 範例
政治敏感詞A
人身攻擊詞B
```

---

### `expressions.yaml`

VTube Studio 表情代碼對應表。

```yaml
happy:    "Expression_Happy"
surprised: "Expression_Surprise"
sarcastic: "Expression_Smirk"
```

---

### `soundboard.yaml`

音效名稱 → 音效檔路徑對應（相對於 `assets/sounds/`）。

```yaml
death:   "death.wav"
victory: "win.wav"
fail:    "fail.wav"
```

---

## 待辦事項

- [ ] 填入 `settings.yaml` 的 `pc_agent.host`（PC 局域網 IP）
- [ ] 填入 `settings.yaml` 的 `discord.token` 與 `discord.notify_channel_id`
- [ ] 填入 `settings.yaml` 的 `vtube_studio.api_url`
- [ ] 填入 `settings.yaml` 的 `twitch` / `youtube` 相關 token（直播平台二選一或全填）
- [ ] 確認 `blocked_keywords.txt` 詞庫內容
- [x] 建立 `config/expressions.yaml`
- [x] 建立 `config/soundboard.yaml`
- [ ] 擴充 `filter.py` 支援熱更新（目前修改 `blocked_keywords.txt` 需重啟才生效）
