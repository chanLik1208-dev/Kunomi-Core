"""
觀眾投票系統。

投票結果僅影響 Kunomi 的台詞，不執行任何遊戲操作。

流程：
  1. vote_start(question, options, duration)
     → 建立投票，開始倒數計時
     → 同時發送投票資訊到 Twitch / YouTube 聊天室（顯示選項）
  2. 觀眾在聊天室輸入選項編號（1 / 2 / 3 ...）
     → chat.twitch / chat.youtube 將訊息送到 /event chat
     → vote_tally() 識別並計票
  3. vote_result()
     → 讀取目前票數，回傳結果供 LLM 生成台詞
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from tools import register_tool

logger = logging.getLogger(__name__)


@dataclass
class VoteSession:
    question: str
    options: list[str]
    end_time: float
    counts: dict[int, int] = field(default_factory=dict)  # {1: 票數, 2: 票數, ...}
    voters: set[str] = field(default_factory=set)          # 每人只能投一票

    @property
    def active(self) -> bool:
        return time.monotonic() < self.end_time

    @property
    def remaining(self) -> int:
        return max(0, int(self.end_time - time.monotonic()))


_current_vote: VoteSession | None = None


def tally(username: str, message: str):
    """
    由 chat 模組呼叫。
    若有進行中的投票且訊息是純數字選項，則計票。
    """
    global _current_vote
    if _current_vote is None or not _current_vote.active:
        return
    msg = message.strip()
    if not msg.isdigit():
        return
    choice = int(msg)
    if choice < 1 or choice > len(_current_vote.options):
        return
    if username in _current_vote.voters:
        return  # 已投過
    _current_vote.voters.add(username)
    _current_vote.counts[choice] = _current_vote.counts.get(choice, 0) + 1
    logger.debug("投票：%s 選 %d（目前：%s）", username, choice, _current_vote.counts)


@register_tool("vote_start")
async def vote_start(question: str, options: list[str], duration: int = 60) -> dict:
    """
    開始一輪觀眾投票。
    question: 投票問題
    options:  選項列表，最多 4 個
    duration: 投票持續秒數（預設 60 秒）
    回傳供 LLM 廣播給觀眾的投票公告文字。
    """
    global _current_vote
    options = options[:4]  # 最多 4 選項
    _current_vote = VoteSession(
        question=question,
        options=options,
        end_time=time.monotonic() + duration,
    )
    logger.info("投票開始：%s（%d 秒）", question, duration)

    announcement = f"【投票開始】{question}\n"
    for i, opt in enumerate(options, 1):
        announcement += f"  {i}. {opt}\n"
    announcement += f"輸入數字投票，{duration} 秒後結束。"

    return {
        "status": "started",
        "question": question,
        "options": options,
        "duration": duration,
        "announcement": announcement,
    }


@register_tool("vote_result")
async def vote_result() -> dict:
    """
    取得目前投票結果。
    若投票仍在進行中，回傳即時票數。
    若投票已結束，回傳最終結果與勝出選項（供 LLM 生成台詞用）。
    """
    if _current_vote is None:
        return {"status": "no_vote", "message": "目前沒有進行中的投票"}

    total = sum(_current_vote.counts.values())
    results = []
    for i, opt in enumerate(_current_vote.options, 1):
        count = _current_vote.counts.get(i, 0)
        pct = round(count / total * 100, 1) if total > 0 else 0.0
        results.append({"index": i, "option": opt, "count": count, "percent": pct})

    results.sort(key=lambda x: x["count"], reverse=True)
    winner = results[0] if results and results[0]["count"] > 0 else None

    return {
        "status": "active" if _current_vote.active else "ended",
        "question": _current_vote.question,
        "remaining_seconds": _current_vote.remaining,
        "total_votes": total,
        "results": results,
        "winner": winner,
    }
