# api/

基於 FastAPI 的本地 Web 控制台，兩機通訊的核心樞紐。

## 啟動方式

```bash
# 從專案根目錄執行
python main.py

# 或直接用 uvicorn（開發模式，自動重載）
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

啟動後可訪問互動文件：`http://localhost:8000/docs`

---

## 端點一覽

### `GET /health`

健康檢查，確認服務存活。

```json
// 回應
{"status": "ok", "character": "Kunomi"}
```

---

### `POST /event`

觸發遊戲事件，回傳 Kunomi 的回應文字。

```json
// 請求
{
  "event_type": "death",
  "context": {}
}

// 回應
{
  "response": "...又死了。第幾次了？",
  "event": "death"
}
```

**event_type 對照表：**

| 值 | 情境 | context 範例 |
|----|------|-------------|
| `death` | 玩家死亡 | `{}` |
| `win` | 遊戲勝利 | `{}` |
| `bug` | 遊戲異常 | `{"bug_description": "角色被彈飛"}` |
| `chat` | 觀眾留言 | `{"username": "Ray", "message": "好厲害"}` |
| `idle` | 冷場自言自語 | `{"seconds": 120}` |
| `voice` | 語音指令 | `{"command": "幫我截圖"}` |
| `vision` | 截圖吐槽 | `{"screen_desc": "血量剩3點還在逛街"}` |

---

### `POST /chat`

快速測試用，直接送觀眾留言。

```json
// 請求
{
  "message": "你好",
  "username": "測試觀眾"
}

// 回應
{
  "response": "...隨便。"
}
```

---

## 錯誤代碼

| 代碼 | 說明 |
|------|------|
| `400` | 訊息被規則過濾器攔截 |
| `500` | LLM 通訊失敗（確認 Ollama 是否在 4070 PC 上運行） |

---

## 未來擴充端點（第二階段後）

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/screenshot` | 觸發 DXcam 截圖並送 Vision 模型 |
| `POST` | `/soundboard/{name}` | 觸發音效板 |
| `GET` | `/memory/recent` | 查詢最近記憶摘要 |
| `POST` | `/vote/start` | 開始觀眾投票（結果僅影響 AI 台詞）|

## 待辦事項

### 目前（第一階段）

- [ ] 實際連接 Ollama 測試 `/chat` 端點是否正常回應
- [ ] 測試過濾器：送含封鎖詞的請求，確認回傳 `400`
- [ ] 確認跨機請求正常（從 4070 PC 呼叫 M4 Mac 上的 FastAPI）

### 第二階段 ✅

- [x] 加入 API Key Header 驗證（`X-API-Key`），避免區網內誤觸
- [x] 加入請求 logging（記錄每次事件觸發與回應，方便 debug）
- [x] 加入全域例外處理，LLM 逾時時回傳友善錯誤訊息（503）而非 500

### 第三階段

- [ ] 實作 `POST /screenshot` 端點（呼叫 `tools/screenshot.py`）
- [ ] 實作 `POST /soundboard/{name}` 端點
- [ ] 實作 `POST /expression/{name}` 端點（觸發 VTube Studio 表情）

### 第四階段

- [ ] 實作 `POST /vote/start` 與 `GET /vote/result` 端點（僅影響 AI 台詞）
- [ ] 實作 `GET /memory/recent` 端點（查詢 ChromaDB 最近 N 筆記憶）
- [ ] 實作 `POST /stream/end` 端點（觸發今日直播總結流程）
