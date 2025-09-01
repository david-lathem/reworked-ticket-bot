import discord
from discord import app_commands
from discord.ext import commands

from utils.access import is_admin
from utils.files import config, save_config
from modules.reaction_module import setup_reaction_roles


class SetupRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="setuproles",
        description="Set up the reaction roles message in a specified channel"
    )
    @app_commands.describe(channel_id="The ID of the channel where the reaction role message will be sent.")
    async def setuproles(self, interaction: discord.Interaction, channel_id: str):
        if not is_admin(interaction):
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        channel = self.bot.get_channel(int(channel_id))
        if channel is None:
            await interaction.response.send_message(
                f"❌ Channel with ID `{channel_id}` not found.",
                ephemeral=True
            )
            return

        emoji_role_map = {
            "📢": 123456789012345678,  # Updates
            "🎉": 987654321098765432   # Giveaway
        }

        message = await setup_reaction_roles(
            self.bot,
            channel_id=channel.id,
            message_text="**Please react below to manage your notification preferences:**\n\n📢 – Stay informed with the latest updates across all our products.\n\n🎉 – Join our community giveaways and exclusive prize events.",
            emoji_role_map=emoji_role_map
        )

        config["reaction_roles_message_id"] = message.id
        config["reaction_roles_channel_id"] = channel.id
        save_config(config)

        await interaction.response.send_message(
            f"✅ Reaction roles message has been posted in {channel.mention}.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupRoles(bot))
