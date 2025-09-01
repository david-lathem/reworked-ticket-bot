import discord
from discord import app_commands
from discord.ext import commands

from utils.files import load_warnings, save_warnings
from utils.access import is_whitelisted_admin
from utils.warn import apply_warning


class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warn", description="Warn a user and log the reason.")
    @app_commands.describe(member="The member to warn", reason="The reason for the warning")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if not is_whitelisted_admin(interaction):
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        await apply_warning(self.bot, member, reason, interaction.channel, issuer=interaction.user)

        await interaction.response.send_message(
            f"✅ {member.mention} has been warned for: **{reason}**",
            ephemeral=True
        )

    @app_commands.command(name="warnings", description="Show all warnings of a user.")
    @app_commands.describe(member="The member to show warnings for")
    async def warnings_command(self, interaction: discord.Interaction, member: discord.Member):
        if not is_whitelisted_admin(interaction):
            return await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
        warnings = load_warnings()
        user_id = str(member.id)
        user_warnings = warnings.get(user_id, [])

        if not user_warnings:
            return await interaction.response.send_message(f"✅ {member.mention} has no warnings.", ephemeral=True)

        embed = discord.Embed(
            title=f"⚠️ Warnings for {member.display_name}", color=0xee00a2)
        for i, warn in enumerate(user_warnings, start=1):
            reason = warn.get("reason", "No reason provided")
            embed.add_field(
                name=f"#{i}", value=f"Reason: {reason}", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarn", description="Clear warnings for a user.")
    @app_commands.describe(member="The member to clear warnings for", amount="Number of warnings to clear or 'all'")
    async def clearwarn(self, interaction: discord.Interaction, member: discord.Member, amount: str):
        if not is_whitelisted_admin(interaction):
            return await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
        warnings = load_warnings()
        user_id = str(member.id)
        if user_id not in warnings:
            return await interaction.response.send_message("✅ User has no warnings.", ephemeral=True)

        if amount.lower() == "all":
            warnings.pop(user_id, None)
            save_warnings(warnings)
            return await interaction.response.send_message(f"✅ All warnings cleared for {member.mention}.", ephemeral=True)

        try:
            amount = int(amount)
        except ValueError:
            return await interaction.response.send_message("❌ Amount must be a number or 'all'.", ephemeral=True)

        current_count = len(warnings[user_id])
        if amount >= current_count:
            warnings.pop(user_id, None)
        else:
            warnings[user_id] = self.warnings[user_id][:-amount]

        save_warnings(warnings)
        await interaction.response.send_message(f"✅ Cleared {amount} warning(s) for {member.mention}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Warnings(bot))
