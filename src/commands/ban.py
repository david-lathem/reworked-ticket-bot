import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from utils.files import load_config, load_shadowbans, save_shadowbans


class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a user from the server with a reason.")
    @app_commands.describe(member="The member to ban", reason="The reason for the ban")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        config = load_config()
        superadmin_role_ids = config["superadmin_role_ids"]

        if not any(role.id in superadmin_role_ids for role in interaction.user.roles):
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot ban yourself.", ephemeral=True)
            return
        if member.id == self.bot.user.id:
            await interaction.response.send_message("❌ You cannot ban the bot.", ephemeral=True)
            return

        try:
            dm_embed = discord.Embed(
                title="You have been banned",
                description=f"You have been banned from **{interaction.guild.name}**.\n\n**Reason:** {reason}",
                color=0xee00a2
            )
            dm_embed.set_footer(text="Cheats.Love")
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        try:
            await member.ban(reason=reason, delete_message_days=1)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I do not have permission to ban this user.", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Unexpected error: `{e}`", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ {member.mention} has been banned for: **{reason}**")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_channel_id = config.get("log_channel_id")
        if log_channel_id:
            logs_channel = interaction.guild.get_channel(log_channel_id)
            if logs_channel:
                log_embed = discord.Embed(
                    title="🚨 User Banned",
                    description=(
                        f"**User:** {member.mention}\n"
                        f"**Issuer:** {interaction.user.mention}\n"
                        f"**Reason:** {reason}"
                    ),
                    color=0xee00a2
                )
                log_embed.set_footer(text=f"Cheats.Love - {now_str}")
                await logs_channel.send(embed=log_embed)

    @app_commands.command(name="shadowban", description="Shadowban a user ID so they are banned instantly upon joining.")
    @app_commands.describe(user_id="The Discord user ID to shadowban", reason="Reason for the shadowban")
    async def shadowban(self, interaction: discord.Interaction, user_id: str, reason: str):
        config = load_config()
        superadmin_role_ids = config["superadmin_role_ids"]

        if not any(role.id in superadmin_role_ids for role in interaction.user.roles):
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        bans = load_shadowbans()

        if any(entry["user_id"] == user_id for entry in bans["shadowbans"]):
            await interaction.response.send_message("⚠️ This user is already shadowbanned.", ephemeral=True)
            return

        bans["shadowbans"].append({
            "user_id": user_id,
            "reason": reason,
            "issuer_id": str(interaction.user.id),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_shadowbans(bans)

        await interaction.response.send_message(f"✅ User ID `{user_id}` has been shadowbanned for: **{reason}**", ephemeral=True)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_channel_id = config.get("log_channel_id")
        if log_channel_id:
            logs_channel = interaction.guild.get_channel(log_channel_id)
            if logs_channel:
                log_embed = discord.Embed(
                    title="🛡️ Shadowban Added",
                    description=(
                        f"**User ID:** {user_id}\n"
                        f"**Issuer:** {interaction.user.mention}\n"
                        f"**Reason:** {reason}"
                    ),
                    color=0xee00a2
                )
                log_embed.set_footer(text=f"Cheats.Love - {now_str}")
                await logs_channel.send(embed=log_embed)


async def setup(bot):
    await bot.add_cog(Ban(bot))
