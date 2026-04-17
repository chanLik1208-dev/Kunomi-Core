import asyncio
import discord
from discord.ext import commands

# 等待確認的使用者集合（shutdown 二次確認用）
_pending_shutdown: set[int] = set()


class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, idle_state: dict):
        self.bot = bot
        self.idle_state = idle_state  # 共享狀態，由 bot.py 傳入

    @commands.command(name="idle")
    async def toggle_idle(self, ctx: commands.Context, mode: str):
        """開關自言自語模式。用法：!idle on / !idle off"""
        if mode.lower() == "on":
            self.idle_state["enabled"] = True
            await ctx.send("自言自語模式已開啟。")
        elif mode.lower() == "off":
            self.idle_state["enabled"] = False
            await ctx.send("自言自語模式已關閉。")
        else:
            await ctx.send("用法：`!idle on` 或 `!idle off`")

    @commands.command(name="shutdown")
    async def shutdown(self, ctx: commands.Context):
        """安全關閉系統（需二次確認）。"""
        _pending_shutdown.add(ctx.author.id)
        await ctx.send("⚠️ 確認關閉系統？請在 15 秒內回覆 `!confirm`")

        def check(m: discord.Message):
            return (
                m.author.id == ctx.author.id
                and m.channel.id == ctx.channel.id
                and m.content.strip().lower() == "!confirm"
            )

        try:
            await self.bot.wait_for("message", check=check, timeout=15)
            await ctx.send("正在關閉系統...")
            await self.bot.close()
        except asyncio.TimeoutError:
            _pending_shutdown.discard(ctx.author.id)
            await ctx.send("已取消，逾時未確認。")
