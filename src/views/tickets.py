import discord

from utils.files import config, save_config, set_ticket_counter, ticket_counter, load_tickets, save_tickets, supporter_emojis
from utils.constants import ticket_category_id, claimed_category_id
from utils.helpers import safe_enqueue_rename
from database.queries import save_ticket_to_mysql


class CreateTicketModal(discord.ui.Modal):
    """Modal to collect ticket information from the user."""

    def __init__(self, user):
        super().__init__(title="Ticket Information")
        self.user = user

        self.order_id = discord.ui.TextInput(
            label="Order ID", placeholder="Enter your order ID")
        self.win_ver = discord.ui.TextInput(
            label="Windows Version", placeholder="Enter your Windows version (type 'winver')")
        self.product = discord.ui.TextInput(
            label="Product", placeholder="Enter the product name")
        self.read_faq = discord.ui.TextInput(
            label="Read FAQ? (yes/no)", placeholder="Have you read the FAQ?")
        self.problem = discord.ui.TextInput(
            label="Problem", style=discord.TextStyle.paragraph, placeholder="Describe your issue")

        self.add_item(self.order_id)
        self.add_item(self.win_ver)
        self.add_item(self.product)
        self.add_item(self.read_faq)
        self.add_item(self.problem)

    async def on_submit(self, interaction: discord.Interaction):
        channel_name = f"ticket-{ticket_counter:04}" if ticket_counter < 1000 else f"ticket-{ticket_counter}"
        set_ticket_counter(1)
        save_config(config)

        guild = interaction.guild
        category = guild.get_channel(ticket_category_id)
        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("Ticket category not found. Please ensure the category ID is correct.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True
            ),
        }

        ticket_viewer_role_ids = config['ticket_viewer_role_ids']
        for role_id in ticket_viewer_role_ids:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True)

        # channel = await category.create_text_channel(channel_name, overwrites=overwrites)
        # await channel.edit(topic=str(self.user.id))
        channel = await category.create_text_channel(channel_name, overwrites=overwrites, topic=str(self.user.id))

        # Tickets in local JSON speichern
        tickets = load_tickets()
        tickets[channel.name] = {
            "creator_id": self.user.id,
            "channel_name": channel_name
        }
        save_tickets(tickets)
        bot = interaction.client

        # Ticket auch in MySQL speichern
        save_ticket_to_mysql(channel.name, self.user.id,
                             channel_name, bot)

        # Embed für die Ticketdaten
        ticket_embed = discord.Embed(
            title="Ticket Details",
            description="Here are the details provided by the user.",
            color=0xee00a2
        )
        ticket_embed.add_field(
            name="Order ID", value=self.order_id.value, inline=False)
        ticket_embed.add_field(name="Windows Version",
                               value=self.win_ver.value, inline=False)
        ticket_embed.add_field(
            name="Product", value=self.product.value, inline=False)
        ticket_embed.add_field(
            name="Read FAQ?", value=self.read_faq.value, inline=False)
        ticket_embed.add_field(name="Problem Description",
                               value=self.problem.value, inline=False)
        ticket_embed.set_footer(text=f"Ticket created by {self.user.name}")

        # Benutzer benachrichtigen
        await interaction.response.send_message(f"Your ticket has been created: {channel.mention}", ephemeral=True)

        # ✅ View & Button erstellen
        view = discord.ui.View(timeout=None)
        claim_button = discord.ui.Button(
            label="Claim", style=discord.ButtonStyle.green)

        # Callback für Claim-Button
        async def claim_callback(interaction_claim: discord.Interaction):
            has_responded = False  # Merker, ob wir bereits geantwortet haben
            try:
                # ✅ Berechtigungen prüfen
                if not any(r.id in ticket_viewer_role_ids for r in interaction_claim.user.roles):
                    await interaction_claim.response.send_message("🚫 You are not authorized to claim tickets.", ephemeral=True)
                    return

                # ✅ Ticket aus Datenbank holen
                select_query = "SELECT claimed FROM tickets WHERE discord_channel_id = %s"
                result = bot.db.execute_query(
                    select_query, (channel.name,), fetch=True)

                if not result:
                    await interaction_claim.response.send_message("⚠ No ticket record found in DB or already claimed.", ephemeral=True)
                    return

                if result[0]["claimed"] != "0":  # Bereits geclaimt
                    await interaction_claim.response.send_message(
                        f"⚠ This ticket has already been claimed by **{result[0]['claimed']}**.",
                        ephemeral=True
                    )
                    return

                # ✅ Ticket in DB als geclaimt markieren
                supporter_tag = f"{interaction_claim.user.name}#{interaction_claim.user.discriminator}"
                update_query = "UPDATE tickets SET claimed = %s WHERE discord_channel_id = %s"
                bot.db.execute_query(
                    update_query, (supporter_tag, channel.name))

                # ✅ Kategorie ändern
                claimed_category = guild.get_channel(claimed_category_id)
                if claimed_category and isinstance(claimed_category, discord.CategoryChannel):
                    await channel.edit(category=claimed_category)
                else:
                    await interaction_claim.response.send_message("⚠ Claimed category not found!", ephemeral=True)
                    return

                # ✅ Umbenennung vorbereiten
                emoji = supporter_emojis.get(
                    str(interaction_claim.user.id), None)
                new_name = f"{emoji}-ticket-{ticket_counter-1:04}" if emoji else f"ticket-{ticket_counter-1:04}"

                # ✅ Rename mit Queue-System
                # Gibt True/False zurück, ob sofort oder queued
                was_immediate = await safe_enqueue_rename(channel, new_name)

                # ✅ DB aktualisieren
                query = "UPDATE tickets SET ticket_number = %s WHERE discord_channel_id = %s;"
                bot.db.execute_query(query, (new_name, str(channel.id)))

                # ✅ Embed posten
                claimed_embed = discord.Embed(
                    title="✅ Ticket Claimed",
                    description=f"This ticket has been claimed by {interaction_claim.user.mention}.",
                    color=0xee00a2
                )
                await channel.send(embed=claimed_embed)

                # ✅ Antworte nur einmal!
                if was_immediate:
                    await interaction_claim.response.send_message("✅ Ticket claimed successfully!", ephemeral=True)
                    has_responded = True
                else:
                    await interaction_claim.followup.send("✅ Ticket claimed successfully! (Rename is queued)", ephemeral=True)
                    has_responded = True

            except Exception as e:
                print(f"[ERROR] Failed to claim ticket: {e}")
                try:
                    if not has_responded:
                        await interaction_claim.response.send_message("❌ Something went wrong while claiming this ticket.", ephemeral=True)
                    else:
                        await interaction_claim.followup.send("❌ Error occurred after response. Please contact admin.", ephemeral=True)
                except Exception as e2:
                    print(f"[CRITICAL] Could not respond to interaction: {e2}")

        # Button in View registrieren
        claim_button.callback = claim_callback
        view.add_item(claim_button)

        # ✅ Embed mit Button in Ticket-Channel senden
        await channel.send(embed=ticket_embed, view=view)


class UserIDModal(discord.ui.Modal):
    """Modal to manually provide a user ID for the transcript."""

    def __init__(self, channel: discord.TextChannel, file_name: str):
        super().__init__(title="Provide User ID")
        self.channel = channel
        self.file_name = file_name

        self.user_id = discord.ui.TextInput(
            label="User ID",
            placeholder="Enter the Discord User ID",
            required=True
        )
        self.add_item(self.user_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id.value)
            user = self.channel.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
            if not user:
                await interaction.response.send_message("The provided User ID is invalid.", ephemeral=True)
                return

            if user.dm_channel is None:
                await user.create_dm()

            await user.dm_channel.send(
                "Here is the transcript of the ticket you requested:",
                file=discord.File(self.file_name)
            )
            await interaction.response.send_message(f"✅ Transcript sent to user with ID {user_id}.", ephemeral=True)

        except discord.NotFound:
            await interaction.response.send_message("❌ The provided User ID does not exist.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid input. Please enter a numeric User ID.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)
