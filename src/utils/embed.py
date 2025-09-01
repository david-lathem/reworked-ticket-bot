import discord

from utils.files import config, save_config
from views.booster import BoosterChannelModal


async def setup_booster_embed(bot):
    booster_lobby_channel_id = config.get("booster_lobby_channel_id")
    if not booster_lobby_channel_id:
        return

    channel = bot.get_channel(booster_lobby_channel_id)
    if not channel:
        print("Booster lobby channel not found.")
        return

    embed = discord.Embed(
        title="Booster’s Private Voice Creation",
        description=(
            "Boosters can click the button below to create a **private** voice channel.\n"
            "Once created, only you have access. You can then use `.invitevoice @User` "
            "to let others join.\n"
            "Use `.removevoice @User` to revoke access."
        ),
        color=0xee00a2
    )
    embed.set_footer(text="Booster Channel System")

    view = discord.ui.View(timeout=None)
    button = discord.ui.Button(
        label="Create Private Voice", style=discord.ButtonStyle.green)

    async def button_callback(interaction: discord.Interaction):
        booster_role_ids = config.get("booster_role", [])
        user_role_ids = [r.id for r in interaction.user.roles]
        if not any(rid in booster_role_ids for rid in user_role_ids):
            return await interaction.response.send_message(
                "You are not a Booster!",
                ephemeral=True
            )
        await interaction.response.send_modal(BoosterChannelModal(interaction.user))

    button.callback = button_callback
    view.add_item(button)

    booster_lobby_message_id = config.get("booster_lobby_message_id")

    if booster_lobby_message_id:
        try:
            existing_message = await channel.fetch_message(booster_lobby_message_id)
            await existing_message.edit(embed=embed, view=view)
            return
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Error editing booster lobby message: {e}")

    new_message = await channel.send(embed=embed, view=view)
    config["booster_lobby_message_id"] = new_message.id
    save_config(config)
