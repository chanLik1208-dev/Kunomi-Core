# tts/

GPT-SoVITS 語音合成模組，運行於 M4 Mac，音訊傳送至 Windows PC 播放。

## 說話流程

```
speak(text)
  → asr.listener.is_speaking = True     （暫停 ASR，防回音）
  → GET http://127.0.0.1:9880?text=...  （GPT-SoVITS 合成 WAV）
  → POST http://PC:8100/tts/play        （傳送 WAV bytes 到 Windows）
  → pc_agent: sounddevice 本地播放      （OBS 可擷取）
  → asr.listener.is_speaking = False    （恢復 ASR 監聽）
```

## 為何在 PC 播放

Windows PC 是直播機，OBS 擷取 PC 的音訊輸出。若 TTS 在 Mac 播放，OBS 收不到聲音。  
Mac 負責合成，PC 負責播放，`/tts/play` 端點阻塞至播完才回應，確保 `is_speaking` 旗標正確。

## 啟動 GPT-SoVITS

GPT-SoVITS 需在 Mac 上獨立啟動，預設監聽 `http://127.0.0.1:9880`：

```bash
cd /path/to/GPT-SoVITS
python api_v2.py -a 127.0.0.1 -p 9880
```

API 格式：
```
GET http://127.0.0.1:9880?text=你好&text_language=zh
→ 回傳 audio/wav
```

## 設定

`config/settings.yaml` 的 `tts` 區段：

| 欄位 | 說明 | 預設值 |
|------|------|--------|
| `api_url` | GPT-SoVITS API 位址 | `http://127.0.0.1:9880` |

`config/settings.yaml` 的 `pc_agent` 區段（播放目標）：

| 欄位 | 說明 |
|------|------|
| `host` | PC Agent 位址（例：`http://192.168.1.XXX:8100`）|
| `api_key` | PC Agent API Key |

## 待辦事項

- [x] GPT-SoVITS API 呼叫
- [x] 說話前後自動設 `asr.listener.is_speaking`
- [x] TTS 不可用時靜默略過（不擋 API 回應）
- [x] 音訊傳送至 Windows PC 播放（`pc_agent /tts/play`）
- [ ] 說話排隊（目前多事件同時觸發可能重疊，需 asyncio.Queue 依序播放）
- [ ] 支援 streaming TTS（逐句合成，減少首字延遲）
