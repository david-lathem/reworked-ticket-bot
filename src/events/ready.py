import discord
from discord.ext import commands


class ReadyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Logged in as {self.bot.user} (ID: {self.bot.user.id})")

        try:
            guild_obj = discord.Object(id=self.bot.DISCORD_GUILD)
            # Copy global to guilds first..
            self.bot.tree.copy_global_to(guild=guild_obj)
            synced = await self.bot.tree.sync(guild=guild_obj)
            print("Synced commands:", [c.name for c in synced])
        except Exception as e:
            import traceback
            print("❌ Slash command sync failed:", e)
            traceback.print_exc()

        # Show current registered slash commands for this guild
        cmds = self.bot.tree.get_commands(
            guild=guild_obj)
        print("Slash commands:", [c.name for c in cmds])


async def setup(bot: commands.Bot):
    await bot.add_cog(ReadyCog(bot))
