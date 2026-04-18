# tools/

Function Calling 工具箱。LLM 輸出 JSON 指令，由此模組 dispatch 到對應函數執行。

## 運作原理

```
LLM 輸出 JSON
  {"tool": "screenshot", "args": {}}
        ↓
  tools.dispatch("screenshot", {})
        ↓
  執行對應工具函數
        ↓
  回傳結果給 LLM / TTS
```

---

## 新增工具方式

在 `tools/` 下建立任意 `.py` 檔，使用 `@register_tool` 裝飾器註冊：

```python
# tools/soundboard.py
from tools import register_tool

@register_tool("soundboard")
async def play_sound(name: str):
    # 播放音效邏輯
    ...
    return {"status": "played", "sound": name}
```

記得在 `main.py` 或 `api/server.py` 中 import 該檔案，讓裝飾器執行。

---

## 計劃工具清單

### 第三階段實作

| 工具名稱 | 檔案 | 說明 |
|---------|------|------|
| `screenshot` | `tools/screenshot.py` | DXcam 截圖，送 Vision 模型吐槽 |
| `soundboard` | `tools/soundboard.py` | 播放預設音效（死亡音、勝利等） |
| `expression` | `tools/expression.py` | pyvts 控制 VTube Studio 表情 |

### 第四階段實作

| 工具名稱 | 檔案 | 說明 |
|---------|------|------|
| `vote_start` | `tools/vote.py` | 開始觀眾投票 |
| `vote_result` | `tools/vote.py` | 讀取投票結果，決定 AI 說話內容 |
| `memory_save` | `tools/memory.py` | 將事件存入 ChromaDB |
| `memory_query` | `tools/memory.py` | 查詢過去相關記憶 |

---

## 注意事項

- 所有工具函數必須是 `async def`
- 工具執行失敗時拋出例外，由呼叫方處理，不在工具內靜默吞掉錯誤
- 涉及遊戲操作的工具（跳崖、換武器）需加安全確認機制，避免 AI 誤觸

## 待辦事項

### 第三階段

- [ ] 建立 `tools/screenshot.py`：呼叫 DXcam 截圖，存檔並回傳路徑
- [ ] 建立 `tools/screenshot.py`：將截圖傳給 Vision 模型，取得畫面描述再觸發 `vision` 事件
- [ ] 建立 `tools/soundboard.py`：讀取 `config/soundboard.yaml`，播放對應音效檔
- [ ] 建立 `tools/expression.py`：透過 pyvts WebSocket 觸發 VTube Studio 表情
- [ ] 建立 `config/soundboard.yaml` 音效對應表
- [ ] 在 `main.py` import 所有工具模組，確保 `@register_tool` 裝飾器執行

### 第四階段

- [ ] 建立 `tools/vote.py`：`vote_start`（開始投票）、`vote_result`（讀取結果，影響 AI 台詞）

### 第五階段

- [ ] 建立 `tools/memory.py`：`memory_save`（存入 ChromaDB）、`memory_query`（語意查詢）
- [ ] 設計記憶 TTL 策略，避免向量庫無限膨脹

### 架構優化

- [ ] 考慮加入工具執行 timeout，防止截圖或網路操作卡住整個 API
- [ ] 工具呼叫結果加入 logging，方便事後查看 AI 觸發了哪些工具
