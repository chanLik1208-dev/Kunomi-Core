import asyncio
import logging
import httpx
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_llm_cfg = _config["llm"]

_MAX_RETRIES = 2


async def chat(prompt: str, system: str = "") -> str:
    """向 Ollama 發送 chat 請求，回傳 AI 回應文字。失敗時最多重試 2 次。"""
    payload = {
        "model": _llm_cfg["model"],
        "messages": [m for m in [
            {"role": "system", "content": system} if system else None,
            {"role": "user", "content": prompt},
        ] if m],
        "stream": False,
    }

    last_err: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 2):
        try:
            async with httpx.AsyncClient(timeout=_llm_cfg["timeout"]) as client:
                resp = await client.post(f"{_llm_cfg['host']}/api/chat", json=payload)
                resp.raise_for_status()
                result = resp.json()["message"]["content"]
                if attempt > 1:
                    logger.info("LLM 第 %d 次重試成功", attempt)
                return result
        except Exception as e:
            last_err = e
            logger.warning("LLM 呼叫失敗（第 %d/%d 次）：%s", attempt, _MAX_RETRIES + 1, e)

    raise RuntimeError(f"LLM 連線失敗，已重試 {_MAX_RETRIES} 次：{last_err}") from last_err


async def chat_with_event(event_type: str, context: dict = {}) -> str:
    """根據事件類型組裝 prompt 後送給 LLM，回應後自動套用 Live2D 情緒參數。"""
    from core.prompt import build_prompt, SYSTEM_PROMPT
    user_prompt = build_prompt(event_type, context)
    logger.debug("觸發事件：%s context=%s", event_type, context)
    response = await chat(prompt=user_prompt, system=SYSTEM_PROMPT)

    # 回應後非同步套用 Live2D 情緒（VTube Studio 未啟動時靜默略過）
    try:
        from tools.live2d import auto_emotion
        asyncio.create_task(auto_emotion(event_type))
    except Exception:
        pass

    return response
