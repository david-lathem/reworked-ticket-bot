import discord
from utils.files import load_booster_channels, config, save_booster_channels


class BoosterChannelModal(discord.ui.Modal):
    """Modal for boosters to enter a private voice channel name."""

    def __init__(self, booster):
        super().__init__(title="Create Booster Voice Channel")
        self.booster = booster
        self.channel_name = discord.ui.TextInput(
            label="Channel Name",
            placeholder="Enter a name for your private channel",
            max_length=50
        )
        self.add_item(self.channel_name)

    async def on_submit(self, interaction: discord.Interaction):
        booster_channels = load_booster_channels()
        owned_channels = [
            cid for cid, owner_id in booster_channels.items()
            if owner_id == str(self.booster.id)
        ]

        if owned_channels:
            return await interaction.response.send_message(
                "You already have a booster channel. Please remove or reuse it first.",
                ephemeral=True
            )

        cat_id = config.get("booster_category_id")
        category = interaction.guild.get_channel(cat_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                "Booster category not found. Please contact an admin.",
                ephemeral=True
            )

        voice_channel = await category.create_voice_channel(
            name=self.channel_name.value,
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=False),
                self.booster: discord.PermissionOverwrite(connect=True, view_channel=True),
            }
        )

        booster_channels[str(voice_channel.id)] = str(self.booster.id)
        save_booster_channels(booster_channels)

        await interaction.response.send_message(
            f"✅ Voice channel **{voice_channel.name}** created!\n"
            f"*(ID: {voice_channel.id})*",
            ephemeral=True
        )
