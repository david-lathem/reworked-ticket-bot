import discord
from discord.ext import commands
import asyncio

from utils.files import load_config, save_config, load_tickets, save_tickets, config
from views.tickets import CreateTicketModal
from utils.checkers import check_inactive_tickets_once, check_booster_channels, reset_ticket_statistics
from utils.embed import setup_booster_embed
from utils.warn import clear_warnings
from modules.giveaway_module import load_giveaways
from modules.activity_tracker import setup as setup_activity
from modules.reaction_module import setup as setup_reaction_module
from modules.nfa_module import setup as setup_nfa
from utils.constants import ticket_category_id


class Startup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.setup_ticket_tool()
        bot = self.bot

        setup_nfa(bot, ticket_category_id=ticket_category_id,
                  admin_role_ids=config['admin_role_ids'])
        # --- NACH DEM START: EINMALIG TICKETS CHECKEN ---
        try:
            # <-- EINMALIGER SOFORT-CHECK
            await check_inactive_tickets_once(bot)
        except Exception as e:
            print(f"[Startup Check] Error during inactivity check: {e}")

        # --- REGELMÄSSIGE TASKS STARTEN (wenn sie noch nicht laufen) ---
        if not hasattr(bot, "bg_task"):
            bot.bg_task = bot.loop.create_task(
                self.check_inactive_tickets())  # läuft alle 5 min

        await setup_booster_embed(bot)
        print("Setup Booster Embed")
        if not hasattr(bot, "booster_check_task"):
            bot.booster_check_task = bot.loop.create_task(
                check_booster_channels(bot))

        if not hasattr(bot, "reset_task"):
            bot.reset_task = bot.loop.create_task(reset_ticket_statistics(bot))

        # --- WARNUNGEN-CLEAR-TASK STARTEN ---
        bot.loop.create_task(clear_warnings())

        # --- GIVEWAY MODULE
        await load_giveaways(bot)
        setup_activity(bot)
        print("Setup Giveaway")
        # --- REACTION MODULE
        setup_reaction_module(bot)
        reaction_roles_channel_id = config.get("reaction_roles_channel_id")
        reaction_roles_message_id = config.get("reaction_roles_message_id")
        print("Setup Reaction")
        # --- SECURITY MODULE
        # setup_security(bot, DISCORD_GUILD) ## NO FILE WAS PRESENT IN ZIP
        # print("Setup Security")
    # 🧠 Map aus config ODER Datenbank laden
        emoji_role_map = {
            "📢": 1376892188964946022,  # Updates role ID
            "🎉": 1376892267482054728   # Giveaway role ID
        }

        if reaction_roles_channel_id and reaction_roles_message_id:
            channel = bot.get_channel(reaction_roles_channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(reaction_roles_message_id)
                    bot.reaction_message_id = message.id
                    bot.emoji_role_map = emoji_role_map  # <-- wichtig!
                    print("✅ Reaction roles restored and active.")

                    # 👇 Falls Emoji fehlt, re-adden
                    existing_reactions = [str(reaction.emoji)
                                          for reaction in message.reactions]

                    for emoji in emoji_role_map:
                        if emoji not in existing_reactions:
                            try:
                                await message.add_reaction(emoji)
                            except discord.HTTPException as e:
                                print(f"❌ Failed to add reaction {emoji}: {e}")

                except discord.NotFound:
                    print("⚠️ Could not find the original reaction roles message.")

    async def check_inactive_tickets(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await check_inactive_tickets_once(self.bot)
            except Exception as e:
                print(f"[Critical] check_inactive_tickets crashed: {e}")

            await asyncio.sleep(60 * 5)  # alle 5 Minuten

    async def setup_ticket_tool(self):
        """Setup or update the ticket tool message in the designated channel."""
        config = load_config()
        tickettool_channel_id = config.get("tickettool_channel_id")

        if not tickettool_channel_id:
            return

        channel = self.bot.get_channel(tickettool_channel_id)
        if not channel:
            print(
                f"❌ Ticket channel with ID {tickettool_channel_id} not found.")
            return

        embed = discord.Embed(
            title="Need Support?",
            description=(
                "If you have an issue or need help, click the button below to create a support ticket. "
                "Our team will assist you as soon as possible."
            ),
            color=0xee00a2
        )
        embed.add_field(
            name="Required Information:",
            value="1. Order ID\n2. Windows version (type 'winver')\n3. Product\n4. Problem description\n5. Have you read the FAQ?",
            inline=False
        )

        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(
            label="Create Ticket", style=discord.ButtonStyle.green)

        async def button_callback(interaction: discord.Interaction):
            config = load_config()
            user_id = str(interaction.user.id)
            tickets = load_tickets()
            to_delete = []

            for t_id, ticket in tickets.items():
                if str(ticket.get("creator_id")) == user_id:
                    channel_obj = None
                    if "channel_id" in ticket:
                        channel_obj = self.bot.get_channel(
                            int(ticket["channel_id"]))
                    if channel_obj is None and "channel_name" in ticket:
                        channel_obj = discord.utils.get(
                            interaction.guild.channels, name=ticket["channel_name"])

                    if channel_obj:
                        await interaction.response.send_message(
                            f"❌ You already have an open ticket: <#{channel_obj.id}>",
                            ephemeral=True
                        )
                        return
                    else:
                        to_delete.append(t_id)

            if to_delete:
                for t_id in to_delete:
                    del tickets[t_id]
                save_tickets(tickets)

            if not config.get("tickets_open", True):
                reason = config["tickets_reason"]
                embed_blocked = discord.Embed(
                    title="Ticket Creation Restricted",
                    description=f"We currently do not accept tickets related to **{reason}**.\nIs your issue related to this?",
                    color=0xee00a2
                )
                view_blocked = discord.ui.View(timeout=None)

                yes_btn = discord.ui.Button(
                    label="Yes", style=discord.ButtonStyle.red)
                no_btn = discord.ui.Button(
                    label="No", style=discord.ButtonStyle.green)

                async def yes_callback(btn_interaction: discord.Interaction):
                    await btn_interaction.response.send_message(
                        f"❌ We cannot accept tickets related to **{reason}** at the moment due to high load.",
                        ephemeral=True
                    )

                async def no_callback(btn_interaction: discord.Interaction):
                    await btn_interaction.response.send_modal(CreateTicketModal(btn_interaction.user))

                yes_btn.callback = yes_callback
                no_btn.callback = no_callback
                view_blocked.add_item(yes_btn)
                view_blocked.add_item(no_btn)

                await interaction.response.send_message(embed=embed_blocked, view=view_blocked, ephemeral=True)
            else:
                await interaction.response.send_modal(CreateTicketModal(interaction.user))

        button.callback = button_callback
        view.add_item(button)

        # Send or update the message
        if "tickettool_message_id" in config:
            try:
                message_id = config["tickettool_message_id"]
                existing_message = await channel.fetch_message(message_id)
                await existing_message.edit(embed=embed, view=view)
            except discord.NotFound:
                new_message = await channel.send(embed=embed, view=view)
                config["tickettool_message_id"] = new_message.id
                save_config(config)
        else:
            new_message = await channel.send(embed=embed, view=view)
            config["tickettool_message_id"] = new_message.id
            save_config(config)


async def setup(bot):
    await bot.add_cog(Startup(bot))
