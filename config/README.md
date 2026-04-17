# config/

系統所有設定檔與靜態資料集中於此，支援熱更新（修改後重啟服務生效）。

## 檔案說明

### `settings.yaml`

全域設定檔，各模組啟動時讀取。

| 區段 | 說明 |
|------|------|
| `llm` | Ollama 主機 IP、模型名稱、逾時秒數 |
| `tts` | GPT-SoVITS API 位址 |
| `asr` | Faster-Whisper 模型大小、按鍵發話設定 |
| `api` | FastAPI 監聽 host / port |
| `discord` | Bot Token、通知頻道 ID |
| `character` | 冷場逾時秒數、自言自語最大循環次數 |
| `filter` | 過濾詞庫路徑、是否啟用 AI 語意過濾 |
| `vtube_studio` | VTube Studio WebSocket 位址 |

**首次設定必填：**
```yaml
llm:
  host: "http://192.168.1.XXX:11434"  # 填入 4070 PC 的局域網 IP

discord:
  token: "your_bot_token_here"
  notify_channel_id: 123456789
```

### `blocked_keywords.txt`

規則過濾詞庫，每行一個封鎖詞，`#` 開頭為注釋。

```
# 範例
政治敏感詞A
人身攻擊詞B
```

修改後下次 API 啟動時自動重新載入（目前為啟動時讀取，如需熱更新需擴充 `filter.py`）。

## 未來擴充

- `expressions.yaml`：VTube Studio 表情代碼對應表（第三階段）
- `soundboard.yaml`：音效板音效名稱 → 檔案路徑對應（第三階段）
- `idle_topics.yaml`：自言自語話題池（第四階段）

## 待辦事項

- [ ] 填入 `settings.yaml` 的 `llm.host`（4070 PC 局域網 IP，格式：`http://192.168.1.XXX:11434`）
- [ ] 填入 `settings.yaml` 的 `discord.token` 與 `discord.notify_channel_id`
- [ ] 填入 `settings.yaml` 的 `vtube_studio.api_url`（VTube Studio 實際 WebSocket 位址）
- [ ] 填入 `settings.yaml` 的 `tts.api_url`（GPT-SoVITS 啟動後確認 port）
- [ ] 建立 `config/expressions.yaml`（第三階段，對應 VTube Studio 表情 ID）
- [ ] 建立 `config/soundboard.yaml`（第三階段，音效名稱 → `.wav` / `.mp3` 路徑）
- [ ] 建立 `config/idle_topics.yaml`（第四階段，自言自語預設話題池）
- [ ] 擴充 `filter.py` 支援熱更新（目前修改 `blocked_keywords.txt` 需重啟才生效）
- [ ] 確認 `blocked_keywords.txt` 詞庫內容，至少加入基本安全詞
