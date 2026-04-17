import logging
import time
import yaml
import discord
from pathlib import Path
from discord.ext import commands
from discord_bot.commands.general import GeneralCommands
from discord_bot.commands.admin import AdminCommands

logger = logging.getLogger(__name__)

_config = yaml.safe_load(Path("config/settings.yaml").read_text(encoding="utf-8"))
_dc_cfg = _config["discord"]

# 共享狀態（idle 開關等，未來可擴充）
_shared_state = {"enabled": True}

# 節流：記錄各類通知最後發送時間
_notify_last: dict[str, float] = {}
_THROTTLE_SEC: int = _dc_cfg.get("notify_throttle_seconds", 30)


def _make_bot() -> commands.Bot:
    allowed_ids: list[int] = _dc_cfg.get("allowed_user_ids", [])

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(
        command_prefix=_dc_cfg.get("command_prefix", "!"),
        intents=intents,
    )

    async def check_allowed(ctx: commands.Context) -> bool:
        if not allowed_ids:
            return True
        if ctx.author.id not in allowed_ids:
            await ctx.send("⛔ 你沒有權限使用此指令。")
            return False
        return True

    bot.add_check(check_allowed)

    @bot.event
    async def on_ready():
        logger.info("Discord Bot 已上線：%s", bot.user)

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ 缺少參數：`{error.param.name}`")
        else:
            logger.error("指令錯誤：%s", error)
            await ctx.send(f"❌ 錯誤：{error}")

    api_key: str = _config.get("api", {}).get("api_key", "")
    bot.add_cog(GeneralCommands(bot, api_key))
    bot.add_cog(AdminCommands(bot))
    return bot


async def send_notify(bot: commands.Bot, category: str, message: str):
    """向通知頻道發送訊息，同類訊息受節流限制。"""
    now = time.time()
    last = _notify_last.get(category, 0)
    if now - last < _THROTTLE_SEC:
        logger.debug("通知節流跳過 [%s]", category)
        return
    _notify_last[category] = now

    channel_id: int = _dc_cfg.get("notify_channel_id", 0)
    if not channel_id:
        return
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(message)


def run():
    token: str = _dc_cfg.get("token", "")
    if not token:
        raise ValueError("discord.token 未設定，請填入 config/settings.yaml")
    bot = _make_bot()
    bot.run(token)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
