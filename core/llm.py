import asyncio
import json
import logging
import re
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


_TOOL_RE = re.compile(r"TOOL:\s*(\{.+\})", re.DOTALL)


def _extract_tool_call(response: str) -> tuple[str, dict | None]:
    """
    從 LLM 回應中拆出說話文字與工具呼叫。
    回傳 (說話文字, tool_dict | None)。
    """
    m = _TOOL_RE.search(response)
    if not m:
        return response.strip(), None
    speech = response[:m.start()].strip()
    try:
        tool = json.loads(m.group(1))
        if "tool" in tool and "args" in tool:
            return speech, tool
    except json.JSONDecodeError:
        pass
    return response.strip(), None


async def chat_with_event(event_type: str, context: dict = {}) -> str:
    """
    根據事件類型組裝 prompt 後送給 LLM。
    - 自動套用 Live2D 情緒
    - 若回應含 TOOL: {...} 則非同步執行工具呼叫
    回傳純說話文字（已去除工具呼叫部分）。
    """
    from core.prompt import build_prompt, SYSTEM_PROMPT
    user_prompt = build_prompt(event_type, context)
    logger.debug("觸發事件：%s context=%s", event_type, context)
    raw = await chat(prompt=user_prompt, system=SYSTEM_PROMPT)

    speech, tool_call = _extract_tool_call(raw)

    # Live2D 情緒（非同步，不阻塞回應）
    try:
        from tools.live2d import auto_emotion
        asyncio.create_task(auto_emotion(event_type))
    except Exception:
        pass

    # 工具呼叫（非同步，不阻塞 TTS）
    if tool_call:
        async def _run_tool():
            from tools import dispatch
            try:
                result = await dispatch(tool_call["tool"], tool_call["args"])
                logger.info("工具執行完成 [%s]：%s", tool_call["tool"], result)
            except Exception as e:
                logger.warning("工具執行失敗 [%s]：%s", tool_call["tool"], e)
        asyncio.create_task(_run_tool())

    return speech
