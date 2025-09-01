import discord
from discord.ext import commands

from utils.files import load_config
from utils.warn import apply_warning
from utils.helpers import update_last_message
from database.queries import save_message_to_mysql


class MessageHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # ---------------- Ticket Messages ----------------
        if "ticket-" in message.channel.name:
            update_last_message(message.channel.name)
            author_id = message.author.id
            author_name = message.author.name
            save_message_to_mysql(message.channel.name,
                                  author_id, author_name, message.content, self. bot)

        # ---------------- Config & Roles ----------------
        config = load_config()
        restricted_roles = config.get("restricted_roles", [])
        whitelist_roles = config.get("whitelist_roles", [])
        bot_whitelist = config.get("bot_whitelist", [])
        log_channel_id = config.get("log_channel_id")

        # ---------------- Handle @everyone / @here ----------------
        if "@everyone" in message.content or "@here" in message.content:
            if not any(role.name in whitelist_roles for role in message.author.roles):
                await message.delete()
                await message.author.send("🚫 You are not allowed to use `@everyone` or `@here`!")
                await apply_warning(
                    self.bot,
                    user=message.author,
                    reason="Used @everyone or @here",
                    channel=message.channel,
                    issuer=message.author,
                    original_message=message.content
                )
                return

        # ---------------- Mentions of restricted users ----------------
        for mentioned_user in message.mentions:
            if mentioned_user.bot:
                continue

            for role in mentioned_user.roles:
                if role.name in restricted_roles:
                    if any(r.name in whitelist_roles for r in message.author.roles):
                        return
                    if message.author.bot and message.author.name in bot_whitelist:
                        return

                    await message.delete()
                    await message.author.send(
                        f"🚫 You are not allowed to mention {mentioned_user.mention} "
                        f"because they have the **{role.name}** role!"
                    )
                    await apply_warning(
                        self.bot,
                        message.author,
                        f"Mentioned restricted user {mentioned_user.display_name}",
                        message.channel
                    )
                    return

        # await self.bot.process_commands(message)


async def setup(bot):
    await bot.add_cog(MessageHandler(bot))
