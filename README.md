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
├── config/         設定檔與過濾詞庫
├── core/           LLM 客戶端、Prompt 模板、過濾器
├── api/            FastAPI 控制台伺服器
├── tools/          Function Calling 工具箱
└── discord_bot/    Discord 遙控器 Bot
```

## 快速啟動

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 填入設定
#    編輯 config/settings.yaml，填入 4070 PC 的局域網 IP

# 3. 4070 PC 啟動 Ollama
ollama run llama3:8b

# 4. M4 Mac 啟動 API 伺服器
python main.py
```

## 開發階段

- [x] 第一階段：LLM 基礎對話 + FastAPI 骨架
- [x] 第二階段：Discord Bot + 雙層過濾器
- [x] 第三階段：DXcam 截圖 + 遊戲事件監聽
- [ ] 第四階段：Faster-Whisper ASR + Idle 自言自語
- [ ] 第五階段：ChromaDB 長期記憶（系統穩定後掛載）

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

### 第三階段（Perception）

- [ ] 實作 `tools/screenshot.py`（DXcam 截圖 + 傳給 Vision 模型）
- [ ] 實作 `tools/soundboard.py`（音效板觸發）
- [ ] 實作 `tools/expression.py`（pyvts VTube Studio 表情控制）
- [ ] 建立 `config/expressions.yaml`（表情代碼對應表）
- [ ] 建立 `config/soundboard.yaml`（音效名稱 → 檔案路徑）
- [ ] Roblox Luau HttpService Webhook 接收器
- [ ] Minecraft Forge 1.20.1 伺服器日誌讀取器（唯讀模式，設讀取間隔）

### 第四階段（Proactive & ASR）

- [ ] 實作 Faster-Whisper ASR 模組（按鍵發話，`alt` 鍵觸發）
- [ ] 實作 Idle State 冷場偵測（超過 `idle_timeout_seconds` 秒觸發）
- [ ] 自言自語迴圈上限控制（最多 `idle_max_loops` 輪）
- [ ] 說話期間暫停 ASR 監聽，避免回音死結

### 第五階段（Memory，系統穩定後）

- [ ] 部署 ChromaDB，建立向量資料庫連線
- [ ] 實作 `tools/memory.py`（`memory_save` / `memory_query`）
- [ ] 直播結束時觸發「今日總結」，更新下次啟動的 System Prompt
- [ ] 設計記憶保留策略（避免向量庫無限膨脹）

### 互動工具箱（節目效果）

- [ ] Twitch 聊天室 API 串接
- [ ] YouTube Live 聊天室 API 串接
- [ ] 觀眾投票系統（`tools/vote.py`）
- [ ] 投票結果執行遊戲操作（需設安全白名單，避免帳號損失）

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
