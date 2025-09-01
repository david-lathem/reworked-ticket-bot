import discord
from discord import app_commands
from discord.ext import commands
from utils.files import load_config


class RolesCog(commands.Cog):
    """Cog for managing allowed roles (give/revoke)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="giverole", description="Assign an allowed role to a user.")
    @app_commands.describe(member="The member to assign the role to", role="The role to assign")
    async def giverole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        config = load_config()
        superadmin_role_ids = config["superadmin_role_ids"]
        allowed_role_ids = config["allowed_role_ids"]

        # Check superadmin permission
        if not any(r.id in superadmin_role_ids for r in interaction.user.roles):
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        # Check if role is allowed
        if role.id not in allowed_role_ids:
            await interaction.response.send_message("❌ This role cannot be assigned.", ephemeral=True)
            return

        # Already has role
        if role in member.roles:
            await interaction.response.send_message(f"⚠️ {member.mention} already has the role `{role.name}`.", ephemeral=True)
            return

        # Assign role
        try:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ {member.mention} has been given the role `{role.name}`.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I do not have permission to assign this role.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Unexpected error: {e}", ephemeral=True)

    @app_commands.command(name="revokerole", description="Remove an allowed role from a user.")
    @app_commands.describe(member="The member to remove the role from", role="The role to remove")
    async def revokerole(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        config = load_config()
        superadmin_role_ids = config["superadmin_role_ids"]
        allowed_role_ids = config["allowed_role_ids"]

        # Check superadmin permission
        if not any(r.id in superadmin_role_ids for r in interaction.user.roles):
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        # Check if role is allowed
        if role.id not in allowed_role_ids:
            await interaction.response.send_message("❌ This role cannot be removed.", ephemeral=True)
            return

        # Member has role
        if role not in member.roles:
            await interaction.response.send_message(f"⚠️ {member.mention} does not have the role `{role.name}`.", ephemeral=True)
            return

        # Remove role
        try:
            await member.remove_roles(role)
            await interaction.response.send_message(f"✅ {member.mention} has had the role `{role.name}` removed.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I do not have permission to remove this role.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Unexpected error: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(RolesCog(bot))
