import httpx
import discord
from discord.ext import commands

API_BASE = "http://127.0.0.1:8000"


class GeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, api_key: str):
        self.bot = bot
        self.headers = {"X-API-Key": api_key} if api_key else {}

    @commands.command(name="health")
    async def health(self, ctx: commands.Context):
        """查詢系統健康狀態。"""
        async with httpx.AsyncClient(timeout=5) as client:
            try:
                resp = await client.get(f"{API_BASE}/health")
                data = resp.json()
                await ctx.send(f"✅ 系統正常 | 角色：{data.get('character', '?')}")
            except Exception as e:
                await ctx.send(f"❌ 無法連線到 API：{e}")

    @commands.command(name="event")
    async def trigger_event(self, ctx: commands.Context, event_type: str, *, extra: str = ""):
        """手動觸發事件。用法：!event death / !event bug 角色被彈飛了"""
        context: dict = {}
        if event_type == "bug" and extra:
            context["bug_description"] = extra
        elif event_type == "idle" and extra.isdigit():
            context["seconds"] = int(extra)

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{API_BASE}/event",
                    json={"event_type": event_type, "context": context},
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    await ctx.send(f"**[{event_type}]** {resp.json()['response']}")
                else:
                    await ctx.send(f"⚠️ API 回傳 {resp.status_code}：{resp.json().get('detail', '未知錯誤')}")
            except Exception as e:
                await ctx.send(f"❌ 請求失敗：{e}")

    @commands.command(name="chat")
    async def chat(self, ctx: commands.Context, *, message: str):
        """讓 Kunomi 回應一則訊息。用法：!chat 你好"""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{API_BASE}/chat",
                    json={"message": message, "username": str(ctx.author.display_name)},
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    await ctx.send(resp.json()["response"])
                else:
                    await ctx.send(f"⚠️ {resp.json().get('detail', '未知錯誤')}")
            except Exception as e:
                await ctx.send(f"❌ 請求失敗：{e}")
