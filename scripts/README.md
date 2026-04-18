# scripts/

自動化部署與啟停腳本。

## 檔案一覽

| 檔案 | 執行環境 | 說明 |
|------|---------|------|
| `deploy_mac.sh` | M4 Mac | 初始部署：建立 venv、安裝依賴、複製設定範本 |
| `start_mac.sh` | M4 Mac | 啟動 FastAPI + Discord Bot |
| `stop_mac.sh` | M4 Mac | 停止所有 Mac 端服務 |
| `deploy_pc.ps1` | Windows PC | 初始部署：建立 venv、安裝依賴、設定防火牆 |
| `start_pc.ps1` | Windows PC | 啟動 PC Agent + Minecraft 監聽 |
| `stop_pc.ps1` | Windows PC | 停止所有 PC 端服務 |
| `health_check.sh` | M4 Mac | 檢查所有服務健康狀態 |

---

## 首次部署流程

### Step 1 — Windows PC

```powershell
H:
cd \OS\Github\chanLik1208-dev\kunomi-core
PowerShell -ExecutionPolicy Bypass -File scripts\deploy_pc.ps1
```

部署完成後：
1. 編輯 `config\settings.yaml`（`api_key`、`pc_agent.api_key`）
2. 放入音效檔到 `assets\sounds\`

### Step 2 — M4 Mac

```bash
bash scripts/deploy_mac.sh
```

部署完成後：
1. 安裝 Ollama：`brew install ollama`
2. 拉取模型：`ollama pull llama3:8b && ollama pull llava:7b`
3. 編輯 `config/settings.yaml`（`pc_agent.host`、`discord.token` 等）

---

## 日常啟動流程

每次直播前：

```
1. Windows PC：.\scripts\start_pc.ps1
2. M4 Mac：    ollama serve（背景執行）
3. M4 Mac：    bash scripts/start_mac.sh
4. 確認：      bash scripts/health_check.sh
```

直播結束後：

```bash
# 觸發今日直播總結
curl -X POST http://localhost:8000/stream/end -H "X-API-Key: YOUR_KEY"

# 停止服務
bash scripts/stop_mac.sh
.\scripts\stop_pc.ps1
```

---

## 日誌位置

| 服務 | 日誌檔 |
|------|--------|
| FastAPI | `logs/api.log` |
| Discord Bot | `logs/discord.log` |
| PC Agent | `logs/pc_agent.log` |
| Minecraft 監聽 | `logs/mc_watcher.log` |

---

## 待辦事項

- [x] Mac 初始部署腳本（`deploy_mac.sh`）
- [x] Mac 啟動腳本（`start_mac.sh`）
- [x] Mac 停止腳本（`stop_mac.sh`）
- [x] PC 初始部署腳本（`deploy_pc.ps1`）
- [x] PC 啟動腳本（`start_pc.ps1`）
- [x] PC 停止腳本（`stop_pc.ps1`）
- [x] 健康檢查腳本（`health_check.sh`）
- [ ] 溫度監控警報（CPU / GPU 超過閾值時發 Discord 通知）
- [ ] 開機自動啟動（Windows 工作排程器 / macOS LaunchAgent）
