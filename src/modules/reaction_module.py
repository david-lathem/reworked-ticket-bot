import discord
from discord.ext import commands

EMBED_COLOR = 0xee00a2


async def setup_reaction_roles(bot, channel_id: int, message_text: str, emoji_role_map: dict):
    """
    Sends an embed with emoji reactions to assign roles.

    :param bot: The Discord bot instance
    :param channel_id: The ID of the channel where the embed should be sent
    :param message_text: The text inside the embed
    :param emoji_role_map: A dictionary like {'🔥': role_id, '🎮': role_id}
    """
    channel = bot.get_channel(channel_id)
    if not channel:
        print(f"❌ Channel with ID {channel_id} not found.")
        return

    embed = discord.Embed(
        title="📌 Choose Your Role",
        description=message_text,
        color=EMBED_COLOR
    )
    embed.set_footer(text="React with an emoji to receive or remove a role.")

    message = await channel.send(embed=embed)

    for emoji in emoji_role_map:
        await message.add_reaction(emoji)

    # Store the message ID and map for future use
    bot.reaction_message_id = message.id
    bot.emoji_role_map = emoji_role_map
    return message


async def handle_reaction(payload, bot, add=True):
    if payload.message_id != getattr(bot, "reaction_message_id", None):
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role_id = bot.emoji_role_map.get(str(payload.emoji))
    if not role_id:
        return

    role = guild.get_role(role_id)
    if not role:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    try:
        if add:
            await member.add_roles(role, reason="Reaction role added")
        else:
            await member.remove_roles(role, reason="Reaction role removed")
    except discord.Forbidden:
        print(
            f"❌ Missing permission to modify role '{role.name}' for {member.display_name}.")
    except Exception as e:
        print(f"⚠️ Error assigning role: {e}")


def setup(bot):
    @bot.event
    async def on_raw_reaction_add(payload):
        await handle_reaction(payload, bot, add=True)

    @bot.event
    async def on_raw_reaction_remove(payload):
        await handle_reaction(payload, bot, add=False)
