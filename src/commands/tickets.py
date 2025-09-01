import discord
from discord.ext import commands
from discord import app_commands
import os

from utils.access import is_admin
from utils.files import config, save_config, load_tickets, save_tickets, supporter_emojis, load_renames, save_renames
from views.tickets import CreateTicketModal, UserIDModal
from utils.helpers import safe_enqueue_rename
from utils.constants import closed_ticket_category_id, ticket_category_id
from utils.transcript import generate_transcript
from database.queries import close_ticket_in_mysql


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tickettool")
    async def tickettool(self, ctx, channel_id: int):
        """Post the ticket embed in the specified channel or update it."""
        if not is_admin(ctx):
            await ctx.send("🚫 You are not authorized to use this command.")
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            await ctx.send(f"❌ Channel with ID `{channel_id}` not found.")
            return

        config['tickettool_channel_id'] = channel_id
        save_config(config)

        embed = discord.Embed(
            title="Need Support?",
            description="If you have an issue or need help, click the button below to create a support ticket. "
                        "Our team will assist you as soon as possible.",
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
            await interaction.response.send_modal(CreateTicketModal(interaction.user))

        button.callback = button_callback
        view.add_item(button)

        if "tickettool_message_id" in config:
            try:
                # Fetch the existing message
                message_id = config["tickettool_message_id"]
                existing_message = await channel.fetch_message(message_id)
                await existing_message.edit(embed=embed, view=view)
                await ctx.send(f"✅ The tickets tool embed has been updated in {channel.mention}.")
            except discord.NotFound:
                new_message = await channel.send(embed=embed, view=view)
                config["tickettool_message_id"] = new_message.id
                save_config(config)
                await ctx.send(f"✅ The ticket tool embed has been placed in {channel.mention}.")
            except Exception as e:
                await ctx.send(f"⚠️ An unexpected error occurred: {e}")
        else:
            new_message = await channel.send(embed=embed, view=view)
            config["tickettool_message_id"] = new_message.id
            save_config(config)
            await ctx.send(f"✅ The ticket tool embed has been placed in {channel.mention}.")

    @app_commands.command(name="escalate", description="Escalate or de-escalate a ticket")
    @app_commands.describe(reason="Reason for escalation")
    async def escalate(self, interaction: discord.Interaction, reason: str):
        channel = interaction.channel
        guild = interaction.guild
        member = interaction.user

        escalated_category = guild.get_channel(config["escalated_category_id"])
        unclaimed_category = guild.get_channel(config["ticket_category_id"])

        ticket_viewer_roles = [guild.get_role(
            rid) for rid in config["ticket_viewer_role_ids"]]
        superadmin_roles = [guild.get_role(rid)
                            for rid in config["superadmin_role_ids"]]

        is_superadmin = any(role in member.roles for role in superadmin_roles)

        tickets = load_tickets()

        raw_name = channel.name
        if "-" in raw_name:
            normalized_name = "-".join(raw_name.split("-")[1:])
        else:
            normalized_name = raw_name

        ticket_key = normalized_name
        ticket = tickets.get(ticket_key)

        if not ticket:
            await interaction.response.send_message(
                f"⚠ No ticket record found for this channel (looking for key: {ticket_key}).", ephemeral=True
            )
            return

        # ✅ Escalate
        if not ticket.get("escalated", False):
            ticket["escalated"] = True
            ticket["escalation_reason"] = reason

            await channel.edit(category=escalated_category)

            for role in ticket_viewer_roles:
                if role:
                    await channel.set_permissions(role, view_channel=False)

            for role in superadmin_roles:
                if role:
                    await channel.set_permissions(role, view_channel=True)

            await interaction.response.send_message(f"✅ Ticket escalated. Reason: **{reason}**")

        # ✅ De-escalate
        else:
            if not is_superadmin:
                await interaction.response.send_message(
                    "❌ Only super admins can de-escalate a ticket.", ephemeral=True
                )
                return

            ticket["escalated"] = False
            ticket.pop("escalation_reason", None)

            # Update DB (set claimed to '0')
            update_query = "UPDATE tickets SET claimed = '0' WHERE discord_channel_id = %s"
            self.bot.db.execute_query(update_query, (channel.name,))

            await channel.edit(category=unclaimed_category)

            for role in ticket_viewer_roles:
                if role:
                    await channel.set_permissions(role, view_channel=True)

            await interaction.response.send_message(
                "✅ Ticket has been de-escalated and is now unclaimed again.", ephemeral=True
            )

        tickets[ticket_key] = ticket
        save_tickets(tickets)

    @app_commands.command(name="managetickets", description="Open or close ticket creation globally.")
    @app_commands.describe(action="Choose 'open' or 'close'", reason="Reason for closing (only for close)")
    async def manage_tickets(self, interaction: discord.Interaction, action: str, reason: str = None):
        superadmin_roles = [interaction.guild.get_role(
            rid) for rid in config["superadmin_role_ids"]]

        if not any(role in interaction.user.roles for role in superadmin_roles):
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        action = action.lower()
        if action not in ["open", "close"]:
            await interaction.response.send_message("❌ Invalid action. Use 'open' or 'close'.", ephemeral=True)
            return

        if action == "open":
            config["tickets_open"] = True
            config["tickets_reason"] = ""
            save_config(config)
            await interaction.response.send_message("✅ Ticket creation is now **OPEN** for everyone.", ephemeral=True)

        elif action == "close":
            if not reason:
                await interaction.response.send_message(
                    "❌ You must provide a reason when closing ticket creation.", ephemeral=True
                )
                return

            config["tickets_open"] = False
            config["tickets_reason"] = reason
            save_config(config)
            await interaction.response.send_message(
                f"✅ Ticket creation is now **CLOSED**.\nReason: **{reason}**", ephemeral=True
            )

  # ----------------------------
    # Rename Ticket Command
    # ----------------------------
    @app_commands.command(name="rename", description="Rename the ticket channel")
    @app_commands.describe(new_name="The new name for the ticket")
    async def rename(self, interaction: discord.Interaction, new_name: str):
        if not is_admin(interaction):
            await interaction.response.send_message("🚫 You are not authorized to rename tickets.", ephemeral=True)
            return

        if "ticket-" not in interaction.channel.name:
            await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)
            return

        if not new_name:
            await interaction.response.send_message("❌ You must specify a new name.", ephemeral=True)
            return

        guild = interaction.guild
        old_name = interaction.channel.name
        tickets = load_tickets()

        # Supporter emoji if exists
        emoji = supporter_emojis.get(str(interaction.user.id), None)

        # Construct new name
        base_name = f"{emoji}-ticket-{new_name}" if emoji else f"ticket-{new_name}"

        # Avoid duplicate channel names
        existing_names = [channel.name for channel in guild.channels]
        final_name = base_name
        counter = 1
        while final_name in existing_names:
            final_name = f"{base_name}-{counter:02d}"
            counter += 1

        # Rename using queue logic
        was_immediate = await safe_enqueue_rename(interaction.channel, final_name)

        # Immediate response to user
        if was_immediate:
            await interaction.response.send_message(f"✅ Channel renamed to `{final_name}`.")
        else:
            await interaction.response.send_message(
                "⚠️ Channel-Rename is currently rate-limited. It was added to the queue.", ephemeral=True
            )

        # Update DB & JSON if rename happened immediately
        if was_immediate and old_name in tickets:
            tickets[final_name] = tickets.pop(old_name)
            tickets[final_name]["channel_name"] = final_name
            save_tickets(tickets)

            query = """
            UPDATE tickets
            SET ticket_number = %s
            WHERE discord_channel_id = %s;
            """
            self.bot.db.execute_query(query, (final_name, old_name))

        print(
            f"[RENAME] {old_name} → {final_name} (queued: {not was_immediate})")

    @app_commands.command(name="close", description="Close the ticket and restrict access.")
    @app_commands.describe(reason="Reason for closing the ticket")
    async def close(self, interaction: discord.Interaction, reason: str):
        if not is_admin(interaction):
            await interaction.response.send_message("🚫 You are not authorized to close tickets.", ephemeral=True)
            return

        if not reason.strip():
            await interaction.response.send_message("⚠️ You must provide a reason to close this ticket.", ephemeral=True)
            return

        channel = interaction.channel
        channel_name = channel.name

        if "ticket-" not in channel_name:
            await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)
            return

        guild = interaction.guild
        tickets = load_tickets()
        ticket_data = tickets.get(channel_name)

        creator = None
        creator_id = None
        valid_creator = True
        transcript_possible = True

        if ticket_data:
            try:
                creator_id = int(ticket_data.get("creator_id"))
                creator = guild.get_member(creator_id) or await guild.fetch_member(creator_id)
            except Exception:
                print(f"Creator with ID {creator_id} could not be found.")
                valid_creator = False
                transcript_possible = False
        else:
            print("Ticket data not found.")
            valid_creator = False
            transcript_possible = False

        ticket_number = channel_name.split("-")[-1]
        new_name = f"closed-{ticket_number}"
        old_name = channel.name

        # Move to closed category
        category = guild.get_channel(closed_ticket_category_id)
        if category and isinstance(category, discord.CategoryChannel):
            await channel.edit(category=category)

        admin_role_ids = config['admin_role_ids']
        ticket_viewer_role_ids = config['ticket_viewer_role_ids']
        # Set permissions
        await channel.set_permissions(guild.default_role, read_messages=False)
        for role_id in admin_role_ids + ticket_viewer_role_ids:
            role = guild.get_role(role_id)
            if role:
                await channel.set_permissions(role, read_messages=True)

        if valid_creator and isinstance(creator, discord.Member):
            await channel.set_permissions(creator, overwrite=None)

        # Rename with queue
        was_immediate = await safe_enqueue_rename(channel, new_name)

        # Transcript
        file_name = f"transcript-{new_name}.txt"
        if transcript_possible:
            transcript = await generate_transcript(channel)
            if os.path.exists(file_name) and isinstance(creator, discord.User):
                try:
                    if creator.dm_channel is None:
                        await creator.create_dm()
                    await creator.dm_channel.send(
                        "Here is the transcript of your closed ticket:",
                        file=discord.File(file_name)
                    )
                    os.remove(file_name)
                except discord.Forbidden:
                    await interaction.followup.send(f"Could not send DM to {creator.mention}.", ephemeral=True)
        else:
            print("Transcript skipped due to missing creator.")

        # Update JSON
        tickets.pop(channel_name, None)
        save_tickets(tickets)
        renames = load_renames()
        renames.pop(str(channel.id), None)
        save_renames(renames)

        # Database log
        close_ticket_in_mysql(
            old_name, interaction.user.name, interaction.user.id, self.bot)

        # Embed with buttons
        embed = discord.Embed(
            title="Ticket Closed",
            description=f"Ticket closed by {interaction.user.mention}\n**Reason:** {reason}",
            color=0xee00a2
        )
        view = discord.ui.View(timeout=None)

        if transcript_possible:
            # Reopen Button
            reopen_button = discord.ui.Button(
                label="Reopen", style=discord.ButtonStyle.green)

            async def reopen_callback(btn_interaction: discord.Interaction):
                await channel.edit(category=guild.get_channel(ticket_category_id))
                if isinstance(creator, discord.Member):
                    await channel.set_permissions(creator, read_messages=True, send_messages=True)
                await btn_interaction.response.send_message("The ticket has been reopened.", ephemeral=True)

            reopen_button.callback = reopen_callback

            # Transcript Button
            transcript_button = discord.ui.Button(
                label="Transcript", style=discord.ButtonStyle.blurple)

            async def transcript_callback(btn_interaction: discord.Interaction):
                if not creator:
                    await btn_interaction.response.send_modal(UserIDModal(channel, file_name))
                else:
                    try:
                        if creator.dm_channel is None:
                            await creator.create_dm()
                        await creator.dm_channel.send(
                            "Here is the transcript of your closed ticket:",
                            file=discord.File(file_name)
                        )
                        await btn_interaction.response.send_message("Transcript sent to the ticket creator.", ephemeral=True)
                        os.remove(file_name)
                    except discord.Forbidden:
                        await btn_interaction.response.send_message("Could not send DM to the ticket creator.", ephemeral=True)

            transcript_button.callback = transcript_callback

            view.add_item(reopen_button)
            view.add_item(transcript_button)

        # Delete Button
        delete_button = discord.ui.Button(
            label="Delete", style=discord.ButtonStyle.red)

        async def delete_callback(btn_interaction: discord.Interaction):
            try:
                if os.path.exists(file_name):
                    os.remove(file_name)
                await btn_interaction.channel.delete()
            except Exception as e:
                print(f"Error while deleting ticket or file: {e}")
                await btn_interaction.response.send_message("An error occurred while trying to delete the ticket.", ephemeral=True)

        delete_button.callback = delete_callback
        view.add_item(delete_button)

        response_msg = "✅ Ticket closed successfully."
        if not was_immediate:
            response_msg += " ⚠ Rename is queued due to rate limit."

        await interaction.response.send_message(response_msg, embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
