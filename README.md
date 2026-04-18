# Kunomi-core

AI VTuber 直播助理系統，驅動冷血毒舌貓耳少女「Kunomi」。

## 硬體架構

| 機器 | 負責模組 |
|------|---------|
| RTX 4070 PC | Ollama LLM、DXcam 截圖、VTube Studio |
| M4 Mac (16GB) | FastAPI 控制台、GPT-SoVITS TTS、Faster-Whisper ASR、ChromaDB |

## 專案結構

```
kunomi-core/
├── config/         設定檔與靜態資料（expressions / soundboard）
├── core/           LLM 客戶端、Prompt 模板、過濾器
├── api/            FastAPI 控制台伺服器（M4 Mac，port 8000）
├── tools/          Function Calling 工具箱
├── discord_bot/    Discord 遙控器 Bot
├── pc_agent/       4070 PC 輕量服務（截圖 / 音效 / 遊戲事件，port 8100）
├── perception/     遊戲事件監聽（Minecraft log / Roblox webhook）
├── asr/            Faster-Whisper 語音辨識（按鍵發話）
├── idle/           冷場偵測與自言自語迴圈
├── memory/         ChromaDB 長期記憶
└── scripts/        自動化部署與啟停腳本
```

## 快速啟動

```bash
# ── 首次部署 ──────────────────────────────────
# 4070 PC（PowerShell 系統管理員）
PowerShell -ExecutionPolicy Bypass -File scripts\deploy_pc.ps1

# M4 Mac
bash scripts/deploy_mac.sh

# ── 日常啟動 ──────────────────────────────────
# 4070 PC
.\scripts\start_pc.ps1

# M4 Mac
bash scripts/start_mac.sh

# 健康確認
bash scripts/health_check.sh
```

## 開發階段

- [x] 第一階段：LLM 基礎對話 + FastAPI 骨架
- [x] 第二階段：Discord Bot + 雙層過濾器
- [x] 第三階段：DXcam 截圖 + 遊戲事件監聽
- [x] 第四階段：Faster-Whisper ASR + Idle 自言自語
- [x] 第五階段：ChromaDB 長期記憶（系統穩定後掛載）

## 待辦事項

### 立即要做

- [ ] 填入 `config/settings.yaml` 的 `llm.host`（4070 PC 局域網 IP）
- [ ] 確認 4070 PC 已安裝 Ollama 並拉取 `llama3:8b` 模型
- [ ] M4 Mac 執行 `pip install -r requirements.txt`
- [ ] 測試 `GET /health` 與 `POST /chat` 端點，確認兩機通訊正常

### 第二階段（Interface & Filter）✅

- [x] 建立 `discord_bot/bot.py`，實作 `!health`、`!event`、`!chat` 指令
- [x] 實作 AI 語意過濾（`core/filter.py` 第二層），啟用 `filter.ai_semantic_filter`
- [x] Discord 通知節流機制（同類事件 30 秒內只發一次）
- [x] 為 FastAPI 加入 API Key 驗證，避免區網內其他裝置誤觸

### 第三階段（Perception）✅

- [x] 實作 `tools/screenshot.py`（DXcam 截圖 + 傳給 Vision 模型）
- [x] 實作 `tools/soundboard.py`（音效板觸發）
- [x] 實作 `tools/expression.py`（pyvts VTube Studio 表情控制）
- [x] 建立 `config/expressions.yaml`（表情代碼對應表）
- [x] 建立 `config/soundboard.yaml`（音效名稱 → 檔案路徑）
- [x] Roblox Luau HttpService Webhook 接收器（`pc_agent/server.py` + `perception/roblox.py` 範本）
- [x] Minecraft Forge 1.20.1 伺服器日誌讀取器（唯讀模式，3 秒間隔）

### 第四階段（Proactive & ASR）✅

- [x] 實作 Faster-Whisper ASR 模組（按鍵發話，`alt` 鍵觸發）
- [x] 實作 Idle State 冷場偵測（超過 `idle_timeout_seconds` 秒觸發）
- [x] 自言自語迴圈上限控制（最多 `idle_max_loops` 輪）
- [x] 說話期間暫停 ASR 監聽（`is_speaking` 旗標）
- [ ] TTS 說話時自動設 `is_speaking = True`（第五階段 TTS 整合時完成）

### 第五階段（Memory）✅

- [x] 部署 ChromaDB，建立向量資料庫連線
- [x] 實作 `tools/memory.py`（`memory_save` / `memory_query`）
- [x] 直播結束時觸發「今日總結」（`POST /stream/end`）
- [x] 過去總結自動注入 System Prompt（啟動時讀取）
- [x] 設計記憶保留策略（`max_events` 上限，自動刪除最舊記錄）

### 互動工具箱（節目效果）

- [ ] Twitch 聊天室 API 串接
- [ ] YouTube Live 聊天室 API 串接
- [ ] 觀眾投票系統（`tools/vote.py`，僅限投票決定 AI 說話內容，不執行遊戲操作）

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查 |
| POST | `/event` | 觸發遊戲事件（death / win / bug / idle / vision） |
| POST | `/chat` | 快速測試：送觀眾留言 |

### 範例請求

```bash
# 觀眾留言
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "username": "測試觀眾"}'

# 觸發死亡事件
curl -X POST http://localhost:8000/event \
  -H "Content-Type: application/json" \
  -d '{"event_type": "death"}'

# 觸發 Bug 事件
curl -X POST http://localhost:8000/event \
  -H "Content-Type: application/json" \
  -d '{"event_type": "bug", "context": {"bug_description": "物理引擎把角色彈飛了"}}'
```
