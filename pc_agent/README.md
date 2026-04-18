# pc_agent/

運行於 Windows 直播 PC 的輕量 FastAPI 服務（port 8100）。負責所有需要直接存取 Windows 硬體的操作。

## 定位

PC 是直播機（OBS、VTube Studio、遊戲全在此），pc_agent 只做輕量的硬體橋接：

| 功能 | 模組 | 說明 |
|------|------|------|
| TTS 音訊播放 | `server.py /tts/play` | 接收 Mac 合成的 WAV，本地播放（OBS 擷取）|
| 螢幕截圖 | `screenshot.py` | DXcam 擷取主螢幕，送 Vision 分析 |
| 音效播放 | `soundboard.py` | pygame 播放音效（死亡音、勝利音等）|
| 遊戲事件接收 | `server.py /game-event` | Roblox / Minecraft Webhook 轉發給 Mac |

## 啟動方式

```powershell
# 在 PC 上，從 kunomi-core 根目錄執行
python pc_agent/main.py
```

監聽 `0.0.0.0:8100`，M4 Mac 透過局域網呼叫。

## 端點一覽

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/tts/play` | 接收 WAV bytes，本地播放（阻塞至完畢）|
| `POST` | `/screenshot` | DXcam 截圖 → Vision 分析 → 推送 AI 吐槽到 Mac |
| `POST` | `/soundboard/{name}` | 播放 `config/soundboard.yaml` 指定音效 |
| `POST` | `/game-event` | 接收遊戲事件，轉發給 Mac FastAPI |

所有端點需帶 `X-API-Key` header（對應 `pc_agent.api_key`）。

## 資料流

```
Mac TTS 合成
  → POST /tts/play (WAV bytes)
  → sounddevice 播放
  → OBS 擷取音訊輸出

Mac 觸發截圖
  → POST /screenshot
  → DXcam 截圖 → llava Vision 分析
  → POST Mac:8000/event vision

遊戲事件（Roblox / Minecraft）
  → POST /game-event
  → POST Mac:8000/event
```

## 安裝依賴

```bash
pip install dxcam opencv-python pygame sounddevice numpy httpx fastapi uvicorn pyyaml
```

## 待辦事項

- [x] `server.py`：截圖、音效、遊戲事件 Webhook
- [x] `/tts/play`：接收 WAV bytes 並本地播放
- [x] Vision 分析（llava via Ollama，已移至 Mac 本機 Ollama）
- [ ] 填入 `config/settings.yaml` 的 `pc_agent.api_key`
- [ ] 確認防火牆開放 port 8100（區網 Private）
- [ ] 安裝 `dxcam`、`sounddevice`、`pygame`
- [ ] 建立 `assets/sounds/` 並放入音效檔
