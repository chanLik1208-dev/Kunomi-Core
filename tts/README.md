# tts/

GPT-SoVITS 語音合成模組（M4 Mac）。

## 說話流程

```
speak(text)
  → asr.listener.is_speaking = True   （暫停 ASR，防回音）
  → GET http://127.0.0.1:9880?text=...（GPT-SoVITS API）
  → 解碼 WAV bytes
  → sounddevice 播放（阻塞至結束）
  → asr.listener.is_speaking = False  （恢復 ASR 監聽）
```

## 整合點

`api/server.py` 的 `/event` 與 `/chat` 端點在回傳回應前自動呼叫 `speak()`。  
TTS 不可用（GPT-SoVITS 未啟動）時靜默略過，不影響 API 回應。

## 啟動 GPT-SoVITS

GPT-SoVITS 需獨立啟動，預設監聽 `http://127.0.0.1:9880`：

```bash
# 在 GPT-SoVITS 目錄下
python api_v2.py -a 127.0.0.1 -p 9880
```

API 格式（單次推理）：
```
GET http://127.0.0.1:9880?text=你好&text_language=zh
```

回傳 `audio/wav` 的 WAV 音訊資料。

## 設定

`config/settings.yaml` 的 `tts` 區段：

| 欄位 | 說明 | 預設值 |
|------|------|--------|
| `api_url` | GPT-SoVITS API 位址 | `http://127.0.0.1:9880` |

## 待辦事項

- [x] GPT-SoVITS API 呼叫
- [x] WAV 解碼 + sounddevice 播放
- [x] 說話前後自動設 `asr.listener.is_speaking`
- [x] TTS 不可用時靜默略過（不擋 API 回應）
- [ ] 支援說話隊列（目前多個事件同時觸發時會重疊，需排隊依序播放）
- [ ] Virtual Audio Cable 路由（讓 TTS 聲音進入 OBS 收音）
