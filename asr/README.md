# asr/

Faster-Whisper 語音辨識模組（Push-to-Talk），運行於 M4 Mac。

## 運作方式

```
按住 alt 鍵 → sounddevice 錄音 → 放開 → Faster-Whisper 辨識
                                              ↓
                             POST /event  {"event_type": "voice", "context": {"command": "..."}}
                                              ↓
                                        Kunomi 語音回應
```

## 回音防護

TTS 播放期間 `asr.listener.is_speaking = True`，錄音迴圈偵測後跳過本輪，避免 AI 錄到自己聲音。  
`tts/speaker.py` 在送出音訊前設為 `True`，pc_agent 播放完畢回應後設回 `False`。

## 設定

`config/settings.yaml` 的 `asr` 區段：

| 欄位 | 說明 | 預設值 |
|------|------|--------|
| `model_size` | Whisper 模型（tiny / base / small / medium / large） | `medium` |
| `language` | 辨識語言代碼 | `zh` |
| `push_to_talk_key` | 觸發鍵（alt / ctrl / shift） | `alt` |

## macOS 權限

首次啟動需授予輔助使用權限（pynput 需要）：  
**系統設定 → 隱私權與安全性 → 輔助使用 → 加入 Terminal 或 Python**

## 啟動方式

由 `main.py` 在服務啟動時自動以背景執行緒啟動：

```python
from asr.listener import start as start_asr
start_asr()
```

## 待辦事項

- [x] 按鍵發話（pynput + sounddevice）
- [x] Faster-Whisper 辨識後送 `/event` voice 事件
- [x] 回音防護旗標（`is_speaking`）與 TTS 整合
- [ ] 支援熱詞增強（`initial_prompt` 填入遊戲常用詞彙，提升辨識率）
- [ ] 辨識結果信心值過濾（低信心不送出，避免雜音誤觸發）
- [ ] Metal 加速（`device="auto"` 讓 Faster-Whisper 使用 M4 GPU）
