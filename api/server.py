import logging
import time
import yaml
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.llm import chat_with_event
from core.filter import rule_filter, semantic_filter, sanitize_response

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_API_KEY: str = _config.get("api", {}).get("api_key", "")

app = FastAPI(title="Kunomi-core API")


# ── 中介層：請求 logging ───────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info("%s %s → %d (%.1fms)", request.method, request.url.path, response.status_code, elapsed)
    return response


# ── 全域例外處理 ───────────────────────────────────────────────────────────────

@app.exception_handler(RuntimeError)
async def llm_error_handler(_request: Request, exc: RuntimeError):
    logger.error("LLM 錯誤：%s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "LLM 目前無法連線，請確認 Ollama 是否在 4070 PC 上運行。"},
    )

@app.exception_handler(Exception)
async def generic_error_handler(_request: Request, exc: Exception):
    logger.exception("未預期錯誤：%s", exc)
    return JSONResponse(status_code=500, content={"detail": "內部錯誤，請查看 server log。"})


# ── API Key 驗證 ───────────────────────────────────────────────────────────────

async def verify_api_key(request: Request):
    if not _API_KEY:
        return
    key = request.headers.get("X-API-Key", "")
    if key != _API_KEY:
        raise HTTPException(status_code=401, detail="無效的 API Key")


# ── 資料模型 ───────────────────────────────────────────────────────────────────

class EventRequest(BaseModel):
    event_type: str
    context: dict = {}

class ChatRequest(BaseModel):
    message: str
    username: str = "觀眾"

class ExpressionRequest(BaseModel):
    name: str
    duration_seconds: float = 2.0


# ── 端點 ──────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "character": "Kunomi"}


@app.post("/event", dependencies=[Depends(verify_api_key)])
async def trigger_event(req: EventRequest):
    if req.event_type == "chat":
        msg = req.context.get("message", "")
        if not rule_filter(msg):
            raise HTTPException(status_code=400, detail="訊息被規則過濾器攔截")
        if not await semantic_filter(msg):
            raise HTTPException(status_code=400, detail="訊息被語意過濾器攔截")

    response = await chat_with_event(req.event_type, req.context)
    response = sanitize_response(response)
    logger.info("事件 [%s] 回應：%s", req.event_type, response[:60])
    return {"response": response, "event": req.event_type}


@app.post("/chat", dependencies=[Depends(verify_api_key)])
async def chat_endpoint(req: ChatRequest):
    if not rule_filter(req.message):
        raise HTTPException(status_code=400, detail="訊息被規則過濾器攔截")
    if not await semantic_filter(req.message):
        raise HTTPException(status_code=400, detail="訊息被語意過濾器攔截")

    response = await chat_with_event(
        "chat", {"username": req.username, "message": req.message}
    )
    response = sanitize_response(response)
    return {"response": response}


@app.post("/screenshot", dependencies=[Depends(verify_api_key)])
async def screenshot():
    """觸發 4070 PC 截圖 → Vision 分析 → Kunomi 吐槽。"""
    from tools.screenshot import screenshot as do_screenshot
    return await do_screenshot()


@app.post("/soundboard/{name}", dependencies=[Depends(verify_api_key)])
async def soundboard(name: str):
    """觸發音效板。name 對應 config/soundboard.yaml 的 key。"""
    from tools.soundboard import play_sound
    return await play_sound(name)


@app.post("/expression", dependencies=[Depends(verify_api_key)])
async def expression(req: ExpressionRequest):
    """觸發 VTube Studio 表情。name 對應 config/expressions.yaml 的 key。"""
    from tools.expression import trigger_expression
    return await trigger_expression(req.name, req.duration_seconds)
