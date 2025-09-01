import discord
from discord import app_commands
from discord.ext import commands

from utils.files import load_booster_channels, save_booster_channels


class Booster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invitevoice", description="Allow a user to join your booster voice channel.")
    @app_commands.describe(user="The user you want to invite")
    async def invitevoice(self, interaction: discord.Interaction, user: discord.Member):
        booster_channels = load_booster_channels()

        # Find owned channel(s)
        owned_channels = [
            cid for cid, owner_id in booster_channels.items()
            if owner_id == str(interaction.user.id)
        ]

        if not owned_channels:
            await interaction.response.send_message("❌ You do not own any booster voice channel.", ephemeral=True)
            return

        channel_id = int(owned_channels[0])
        voice_channel = interaction.guild.get_channel(channel_id)

        if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
            booster_channels.pop(str(channel_id), None)
            save_booster_channels(booster_channels)
            await interaction.response.send_message(
                "❌ Your booster voice channel no longer exists. It has been removed from the system.",
                ephemeral=True
            )
            return

        await voice_channel.set_permissions(user, connect=True, view_channel=True)
        await interaction.response.send_message(f"✅ {user.mention} can now join **{voice_channel.name}**.")

    @app_commands.command(name="removevoice", description="Remove a user's access to your booster voice channel.")
    @app_commands.describe(user="The user you want to remove from your channel")
    async def removevoice(self, interaction: discord.Interaction, user: discord.Member):
        booster_channels = load_booster_channels()

        # Find owned channel(s)
        owned_channels = [
            cid for cid, owner_id in booster_channels.items()
            if owner_id == str(interaction.user.id)
        ]

        if not owned_channels:
            await interaction.response.send_message("❌ You do not own any booster voice channel.", ephemeral=True)
            return

        channel_id = int(owned_channels[0])
        voice_channel = interaction.guild.get_channel(channel_id)

        if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
            booster_channels.pop(str(channel_id), None)
            save_booster_channels(booster_channels)
            await interaction.response.send_message(
                "❌ Your booster voice channel no longer exists. It has been removed from the system.",
                ephemeral=True
            )
            return

        await voice_channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"✅ Removed {user.mention} from **{voice_channel.name}**.")


async def setup(bot):
    await bot.add_cog(Booster(bot))
