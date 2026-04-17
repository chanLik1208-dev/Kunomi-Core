# scripts/

自動化部署與啟停腳本。

## 檔案一覽

| 檔案 | 執行環境 | 說明 |
|------|---------|------|
| `deploy_mac.sh` | M4 Mac | 初始部署：建立 venv、安裝依賴、複製設定範本 |
| `start_mac.sh` | M4 Mac | 啟動 API 服務 + Discord Bot |
| `stop_mac.sh` | M4 Mac | 停止所有 Mac 端服務 |
| `deploy_pc.ps1` | 4070 PC | 初始部署：建立 venv、安裝依賴、設定防火牆 |
| `start_pc.ps1` | 4070 PC | 啟動 Ollama + PC Agent + Minecraft 監聽 |
| `stop_pc.ps1` | 4070 PC | 停止所有 PC 端服務 |
| `health_check.sh` | M4 Mac | 一次性檢查所有服務健康狀態 |

---

## 首次部署流程

### Step 1 — 4070 PC

```powershell
# 以系統管理員身份執行 PowerShell
PowerShell -ExecutionPolicy Bypass -File scripts\deploy_pc.ps1
```

部署完成後：
1. 編輯 `config\settings.yaml`
2. 執行 `ollama pull llama3:8b` 與 `ollama pull llava:7b`
3. 放入音效檔到 `assets\sounds\`

### Step 2 — M4 Mac

```bash
bash scripts/deploy_mac.sh
```

部署完成後：
1. 編輯 `config/settings.yaml`（填入 4070 PC 的局域網 IP）

---

## 日常啟動流程

每次直播前執行順序：

```
1. 4070 PC：.\scripts\start_pc.ps1
2. M4 Mac： bash scripts/start_mac.sh
3. 確認：   bash scripts/health_check.sh
```

直播結束後：

```bash
# M4 Mac：觸發今日總結存入 ChromaDB
curl -X POST http://localhost:8000/stream/end \
  -H "X-API-Key: YOUR_KEY"

# 停止所有服務
bash scripts/stop_mac.sh          # M4 Mac
.\scripts\stop_pc.ps1             # 4070 PC
```

---

## 選用參數

```bash
# M4 Mac：不啟動 Discord Bot
bash scripts/start_mac.sh --no-discord

# M4 Mac：不啟動 ASR
bash scripts/start_mac.sh --no-asr

# 4070 PC：不啟動 Ollama（已在背景運行）
.\scripts\start_pc.ps1 -NoOllama

# 4070 PC：不啟動 Minecraft 監聽
.\scripts\start_pc.ps1 -NoMinecraft
```

---

## 日誌位置

| 服務 | 日誌檔 |
|------|--------|
| FastAPI | `logs/api.log` |
| Discord Bot | `logs/discord.log` |
| PC Agent | `logs/pc_agent.log` |
| Ollama | `logs/ollama.log` |
| Minecraft 監聽 | `logs/mc_watcher.log` |

## 待辦事項

- [x] M4 Mac 初始部署腳本（`deploy_mac.sh`）
- [x] M4 Mac 啟動腳本（`start_mac.sh`）
- [x] M4 Mac 停止腳本（`stop_mac.sh`）
- [x] 4070 PC 初始部署腳本（`deploy_pc.ps1`）
- [x] 4070 PC 啟動腳本（`start_pc.ps1`）
- [x] 4070 PC 停止腳本（`stop_pc.ps1`）
- [x] 健康檢查腳本（`health_check.sh`）
- [ ] 溫度監控警報（CPU / GPU 超過閾值時發 Discord 通知）
- [ ] 開機自動啟動（Windows 工作排程器 / macOS LaunchAgent）
