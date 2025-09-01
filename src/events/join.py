import discord
from discord.ext import commands
from utils.files import load_shadowbans, load_config


class JoinEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = load_config()
        bans = load_shadowbans()

        for entry in bans.get("shadowbans", []):
            if entry["user_id"] == str(member.id):
                reason = entry["reason"]

                # Try sending DM
                try:
                    dm_embed = discord.Embed(
                        title="You have been banned",
                        description=f"You have been banned from **{member.guild.name}**.\n\n**Reason:** {reason}",
                        color=0xee00a2
                    )
                    await member.send(embed=dm_embed)
                except discord.Forbidden:
                    pass

                # Ban the member
                try:
                    await member.ban(reason=f"Shadowban: {reason}", delete_message_days=1)
                except discord.Forbidden:
                    print(
                        f"⚠️ Could not ban {member.id}. Missing permissions.")

                # Log the shadowban
                log_channel_id = config.get("log_channel_id")
                if log_channel_id:
                    logs_channel = member.guild.get_channel(log_channel_id)
                    if logs_channel:
                        embed = discord.Embed(
                            title="🚨 Shadowban Triggered",
                            description=f"**User:** {member.mention} ({member.id})\n**Reason:** {reason}",
                            color=0xee00a2
                        )
                        await logs_channel.send(embed=embed)
                break


async def setup(bot):
    await bot.add_cog(JoinEvents(bot))
