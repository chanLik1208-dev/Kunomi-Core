import logging
from tools import register_tool

logger = logging.getLogger(__name__)


@register_tool("memory_save")
async def memory_save(content: str, event_type: str = "general", metadata: dict = {}) -> dict:
    """
    將遊戲事件或有趣片段存入 ChromaDB 長期記憶。
    event_type 建議使用：death / win / bug / funny / chat_highlight
    """
    from memory.store import save_event
    mid = save_event(event_type, content, metadata)
    logger.info("記憶儲存完成：id=%s", mid)
    return {"status": "saved", "id": mid, "event_type": event_type}


@register_tool("memory_query")
async def memory_query(query: str, n_results: int = 5) -> dict:
    """
    語意查詢過去的遊戲事件記憶。
    回傳最相關的 n_results 筆，供 LLM 做為背景知識。
    """
    from memory.store import query_events
    results = query_events(query, n_results)
    logger.info("記憶查詢「%s」：找到 %d 筆", query[:30], len(results))
    return {"results": results, "count": len(results)}
