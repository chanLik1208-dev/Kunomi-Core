# pc_agent/

運行於 RTX 4070 PC 的輕量 FastAPI 服務（port 8100），負責所有需要直接存取 Windows 硬體的操作。

## 負責項目

| 功能 | 模組 | 說明 |
|------|------|------|
| 螢幕截圖 | `screenshot.py` | DXcam 擷取主螢幕，fallback 用 PIL |
| 音效播放 | `soundboard.py` | pygame 播放音效，fallback 用 winsound |
| Vision 分析 | `server.py` | 截圖送 Ollama llava 模型分析 |
| 遊戲事件接收 | `server.py` | 接收 Roblox / Minecraft 推送的 Webhook |

## 啟動方式

```bash
# 在 4070 PC 上，從 kunomi-core 根目錄執行
python pc_agent/main.py
```

啟動後監聽 `0.0.0.0:8100`，M4 Mac 透過局域網呼叫。

## 安裝依賴（4070 PC 專屬）

```bash
pip install dxcam opencv-python pygame httpx fastapi uvicorn pyyaml
```

> dxcam 需要 DirectX，僅支援 Windows。

## 端點一覽

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/screenshot` | 截圖 → Vision 分析 → 推送 AI 吐槽到 M4 Mac |
| `POST` | `/soundboard/{name}` | 播放 `config/soundboard.yaml` 指定音效 |
| `POST` | `/game-event` | 接收 Roblox / Minecraft 遊戲事件，轉發給 M4 Mac |

所有端點需帶 `X-API-Key` header（與 `config/settings.yaml` 的 `pc_agent.api_key` 相同）。

## 資料流

```
截圖請求（M4 Mac）
  → POST /screenshot
  → DXcam 截圖
  → Ollama llava 分析畫面
  → POST http://M4-Mac:8000/event  {"event_type": "vision", "context": {"screen_desc": "..."}}
  → Kunomi 吐槽回應
```

```
遊戲事件（Roblox / Minecraft）
  → POST /game-event
  → 驗證 webhook_secret
  → POST http://M4-Mac:8000/event
  → Kunomi 回應
```

## 待辦事項

- [x] `screenshot.py`：DXcam 截圖 + PIL fallback
- [x] `soundboard.py`：pygame 播放 + winsound fallback
- [x] `server.py`：截圖端點、音效端點、遊戲事件 Webhook
- [x] Vision 分析（llava via Ollama）
- [ ] 填入 `config/settings.yaml` 的 `pc_agent.host`（4070 PC 局域網 IP）
- [ ] 確認防火牆開放 port 8100（區網內）
- [ ] 在 4070 PC 安裝 `dxcam`、`opencv-python`、`pygame`
- [ ] 建立 `assets/sounds/` 資料夾，放入音效檔（對應 `config/soundboard.yaml`）
- [ ] 確認 Ollama 已拉取 Vision 模型：`ollama pull llava:7b`
