import discord
from discord.ext import commands

# IDs wie gewünscht
NFA_CATEGORY_ID = 1383775291260014632
NFA_ROLE_ID = 1383774708415074354

def setup(bot, ticket_category_id, admin_role_ids):
    @bot.command(name="nfa")
    async def move_to_nfa(ctx):
        if not any(role.id in admin_role_ids for role in ctx.author.roles):
            await ctx.send("🚫 You are not authorized to use this command.")
            return

        channel = ctx.channel
        guild = ctx.guild
        nfa_role = guild.get_role(NFA_ROLE_ID)

        # Kategorie ändern
        await channel.edit(category=guild.get_channel(NFA_CATEGORY_ID))

        # Berechtigungen zurücksetzen
        await channel.set_permissions(guild.default_role, read_messages=False)

        if nfa_role:
            await channel.set_permissions(nfa_role, read_messages=True, send_messages=True)

        for role_id in admin_role_ids:
            role = guild.get_role(role_id)
            if role:
                await channel.set_permissions(role, overwrite=None)

        await ctx.send("✅ Ticket was moved to the NFA category. Please wait.")

    @bot.command(name="nfa1")
    async def move_back_from_nfa(ctx):
        if not any(role.id in admin_role_ids for role in ctx.author.roles):
            await ctx.send("🚫 You are not authorized to use this command.")
            return

        channel = ctx.channel
        guild = ctx.guild
        nfa_role = guild.get_role(NFA_ROLE_ID)

        # Kategorie zurücksetzen
        await channel.edit(category=guild.get_channel(ticket_category_id))

        # Berechtigungen zurücksetzen
        await channel.set_permissions(guild.default_role, read_messages=False)

        if nfa_role:
            await channel.set_permissions(nfa_role, overwrite=None)

        for role_id in admin_role_ids:
            role = guild.get_role(role_id)
            if role:
                await channel.set_permissions(role, read_messages=True, send_messages=True)

        await ctx.send("✅ Ticket was transfered back to support.")
