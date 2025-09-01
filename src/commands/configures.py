import discord
from discord import app_commands
from discord.ext import commands

from utils.files import config, supporter_emojis, save_emojis, set_supporter_emoji


class ConfiguresCog(commands.Cog):
    """Cog to manage configuration commands such as assigning supporter emojis."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="setemoji",
        description="Assign an emoji to a supporter for claimed tickets."
    )
    @app_commands.describe(
        user="The supporter to assign the emoji to",
        emoji="The emoji to assign"
    )
    async def setemoji(self, interaction: discord.Interaction, user: discord.Member, emoji: str):
        # Permission check for superadmins
        if not any(role.id in config["superadmin_role_ids"] for role in interaction.user.roles):
            await interaction.response.send_message(
                "🚫 You are not authorized to use this command.", ephemeral=True
            )
            return

        # Update in-memory dictionary
        set_supporter_emoji(str(user.id), emoji)
        save_emojis()

        await interaction.response.send_message(
            f"✅ {user.mention} has been assigned the emoji `{emoji}` for claimed tickets.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ConfiguresCog(bot))
