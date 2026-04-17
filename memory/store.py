"""
ChromaDB 長期記憶模組。

兩個 collection：
- events：遊戲中有趣事件、失敗經驗（永久保留，定期清理舊資料）
- sessions：每次直播的今日總結（用於更新下次啟動的 System Prompt）
"""
import logging
import time
import uuid
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_DB_PATH = _config.get("memory", {}).get("db_path", "chroma_db")
_MAX_EVENTS = _config.get("memory", {}).get("max_events", 500)

_client = None
_events_col = None
_sessions_col = None


def _get_client():
    global _client, _events_col, _sessions_col
    if _client is not None:
        return _client
    try:
        import chromadb
    except ImportError:
        raise RuntimeError("chromadb 未安裝，請執行 pip install chromadb")

    _client = chromadb.PersistentClient(path=_DB_PATH)
    _events_col = _client.get_or_create_collection("events")
    _sessions_col = _client.get_or_create_collection("sessions")
    logger.info("ChromaDB 已連線（路徑：%s）", _DB_PATH)
    return _client


def save_event(event_type: str, content: str, metadata: dict | None = None) -> str:
    """儲存一筆遊戲事件到記憶體，回傳記憶 ID。"""
    _get_client()
    mid = str(uuid.uuid4())
    meta = {
        "event_type": event_type,
        "timestamp": int(time.time()),
        **(metadata or {}),
    }
    _events_col.add(documents=[content], metadatas=[meta], ids=[mid])
    logger.debug("記憶儲存 [%s]：%s", event_type, content[:60])

    # 超過上限時刪除最舊的記錄
    count = _events_col.count()
    if count > _MAX_EVENTS:
        oldest = _events_col.get(
            where={},
            limit=count - _MAX_EVENTS,
            include=["metadatas"],
        )
        if oldest["ids"]:
            _events_col.delete(ids=oldest["ids"])
            logger.info("記憶清理：刪除 %d 筆舊事件", len(oldest["ids"]))

    return mid


def query_events(query: str, n_results: int = 5) -> list[dict]:
    """語意查詢最相關的事件記憶，回傳 [{content, metadata, distance}]。"""
    _get_client()
    count = _events_col.count()
    if count == 0:
        return []
    results = _events_col.query(
        query_texts=[query],
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "content": doc,
            "metadata": meta,
            "distance": dist,
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]


def save_session_summary(summary: str, date: str) -> str:
    """儲存今日直播總結，回傳 session ID。"""
    _get_client()
    sid = f"session_{date}"
    existing = _sessions_col.get(ids=[sid])
    if existing["ids"]:
        _sessions_col.update(
            ids=[sid],
            documents=[summary],
            metadatas=[{"date": date, "timestamp": int(time.time())}],
        )
    else:
        _sessions_col.add(
            ids=[sid],
            documents=[summary],
            metadatas=[{"date": date, "timestamp": int(time.time())}],
        )
    logger.info("Session 總結已儲存（%s）", date)
    return sid


def get_recent_summaries(n: int = 3) -> list[str]:
    """取得最近 n 次直播的總結，用於注入 System Prompt。"""
    _get_client()
    count = _sessions_col.count()
    if count == 0:
        return []
    results = _sessions_col.get(
        where={},
        limit=min(n, count),
        include=["documents", "metadatas"],
    )
    # 依 timestamp 降冪排序
    pairs = sorted(
        zip(results["documents"], results["metadatas"]),
        key=lambda x: x[1].get("timestamp", 0),
        reverse=True,
    )
    return [doc for doc, _ in pairs[:n]]
