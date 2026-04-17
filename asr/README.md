# asr/

Faster-Whisper 語音辨識模組，運行於 M4 Mac（CPU 模式）。

## 運作方式

```
按住 alt 鍵 → sounddevice 錄音 → 放開 → Faster-Whisper 辨識
                                              ↓
                                 POST /event  {"event_type": "voice", "context": {"command": "..."}}
```

## 回音防護

TTS 說話期間 `asr.listener.is_speaking = True`，錄音迴圈偵測到後跳過本輪，避免 AI 錄到自己聲音。  
TTS 模組說話結束後須手動將此旗標設回 `False`（第五階段 TTS 整合時處理）。

## 啟動方式

ASR 由 `main.py` 在服務啟動時自動以背景執行緒啟動：

```python
from asr.listener import start as start_asr
start_asr()
```

macOS 首次啟動需在「系統設定 → 隱私權與安全性 → 輔助使用」授予 Terminal / Python 權限，  
否則 pynput 無法監聽鍵盤。

## 設定

在 `config/settings.yaml` 的 `asr` 區段調整：

| 欄位 | 說明 | 預設值 |
|------|------|--------|
| `model_size` | Whisper 模型大小（tiny / base / small / medium / large） | `medium` |
| `language` | 辨識語言代碼 | `zh` |
| `push_to_talk_key` | 按鍵發話觸發鍵（alt / ctrl / shift） | `alt` |

## 待辦事項

- [x] 實作按鍵發話（pynput + sounddevice）
- [x] Faster-Whisper 辨識後送 `/event` voice 事件
- [x] 回音防護旗標（`is_speaking`）
- [ ] 整合 TTS 模組，TTS 說話時自動設 `is_speaking = True`（第五階段）
- [ ] 支援熱詞增強（Whisper `initial_prompt` 填入遊戲常用詞彙，提升辨識率）
- [ ] 辨識結果信心值過濾（低信心時不送出，避免雜音誤觸發）
