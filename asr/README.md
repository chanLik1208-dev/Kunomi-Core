# asr/

> **注意：STT 已移至 Windows PC（`pc_agent/asr.py`）執行。**
>
> 麥克風在直播 PC，ASR 在同一台可直接擷取音訊，也不需要 macOS 輔助使用權限。

此目錄保留供未來擴充（例如串流 ASR、多語言切換等）。

## 現行架構

```
Windows PC
  pynput 偵測 Alt 鍵
    → sounddevice 錄音
    → Faster-Whisper 辨識（CUDA 加速）
    → POST Mac:8000/event  {"event_type": "voice", "command": "..."}
```

## 回音防護

`pc_agent/asr.py` 的 `is_speaking` flag 由 `pc_agent/server.py` 的 `/tts/play` 端點控制：
- TTS 播放前設為 `True` → ASR 跳過錄音
- 播放結束後設回 `False` → 恢復監聽

## 設定

`config/settings.yaml` 的 `asr` 區段（PC 讀取）：

| 欄位 | 說明 | 預設值 |
|------|------|--------|
| `model_size` | Whisper 模型（tiny / base / small / medium / large） | `medium` |
| `language` | 辨識語言代碼 | `zh` |
| `push_to_talk_key` | 觸發鍵（alt / ctrl / shift） | `alt` |

`config/settings.yaml` 的 `api.mac_host`（PC 送結果用）：
```yaml
api:
  mac_host: "http://192.168.1.XXX:8000"  # Mac 的局域網 IP
```

## 待辦事項

- [x] 按鍵發話（pynput + sounddevice）— `pc_agent/asr.py`
- [x] Faster-Whisper CUDA 加速（`device="auto"`）
- [x] 回音防護（`is_speaking` 由 `/tts/play` 端點控制）
- [x] 辨識結果送 Mac FastAPI `/event` voice 事件
- [ ] 熱詞增強（`initial_prompt` 填入遊戲常用詞彙）
- [ ] 辨識信心值過濾（低信心不送出）
