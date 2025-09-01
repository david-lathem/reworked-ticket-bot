import discord
from discord import app_commands
from discord.ext import commands

from utils.access import is_admin
from utils.checkers import check_inactive_tickets_once


class CheckersCog(commands.Cog):
    """Background task management commands (status, force checks, etc.)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="status",
        description="Check if background tasks are still running."
    )
    async def status(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            await interaction.response.send_message(
                "🚫 You are not authorized to use this command.", ephemeral=True
            )
            return

        status_lines = []

        if hasattr(self.bot, "bg_task") and not self.bot.bg_task.done():
            status_lines.append("✅ `check_inactive_tickets` is running.")
        else:
            status_lines.append("❌ `check_inactive_tickets` has stopped.")

        if hasattr(self.bot, "booster_check_task") and not self.bot.booster_check_task.done():
            status_lines.append("✅ `check_booster_channels` is running.")
        else:
            status_lines.append("❌ `check_booster_channels` has stopped.")

        if hasattr(self.bot, "reset_task") and not self.bot.reset_task.done():
            status_lines.append("✅ `reset_ticket_statistics` is running.")
        else:
            status_lines.append("❌ `reset_ticket_statistics` has stopped.")

        await interaction.response.send_message("\n".join(status_lines), ephemeral=True)

    @app_commands.command(
        name="force_check",
        description="Force an inactivity check for tickets."
    )
    async def force_check(self, interaction: discord.Interaction):
        if not is_admin(interaction):
            await interaction.response.send_message(
                "🚫 You are not authorized to use this command.", ephemeral=True
            )
            return

        try:
            await check_inactive_tickets_once(self.bot)
            await interaction.response.send_message(
                "✅ Inactivity check forced successfully!", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error during inactivity check: `{e}`", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(CheckersCog(bot))
