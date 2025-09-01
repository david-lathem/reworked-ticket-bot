import discord
from discord import app_commands
from discord.ext import commands

from utils.files import load_tickets, config, load_troubleshoot_data
from views.submit import SubmitDX11Modal
from utils.constants import EMBED_COLOR, PRODUCTS

admin_role_ids = config['admin_role_ids']
ticket_viewer_role_ids = config['ticket_viewer_role_ids']


class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 📌 Review
    @app_commands.command(name="review", description="Ask customer for a review.")
    async def review(self, interaction: discord.Interaction):
        if "ticket-" not in interaction.channel.name:
            await interaction.response.send_message(
                "❌ This command can only be used in a ticket channel.", ephemeral=True
            )
            return

        tickets = load_tickets()
        ticket_data = tickets.get(interaction.channel.name)

        if not ticket_data:  # error1337
            await interaction.response.send_message(
                "❌ Could not find ticket information.", ephemeral=True
            )
            return

        creator_id = ticket_data.get("creator_id")
        creator_mention = f"<@{creator_id}>" if creator_id else "the ticket creator"

        embed = discord.Embed(
            title="We'd Love Your Feedback! ⭐",
            description=(
                f"If you have a moment, {creator_mention}, "
                "we'd love to hear your feedback in <#1008146041805226014>!\n\n"
                "Of course, it's completely optional. Have a great day and enjoy the game! 🎮"
            ),
            color=0xee00a2,
        )
        embed.set_footer(text="Thank you for your support!")

        await interaction.response.send_message(embed=embed)

    # 📌 Resellers
    @app_commands.command(name="resellers", description="Provides information about the reseller program.")
    async def resellers(self, interaction: discord.Interaction):
        if not any(role.id in admin_role_ids for role in interaction.user.roles):
            await interaction.response.send_message(
                "🚫 You are not authorized to use this command.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🤝 Reseller Program Information",
            description=(
                "Thank you for your interest in our **Reseller Program**!\n"
                "To get started, please provide the following details:\n\n"
                "🌐 **Do you have a website?** If yes, please share the link\n"
                "📎 **Your Discord server or community link**\n\n"
                "**📌 Important Information:**\n"
                "⚠️ First purchase must be **at least $100** – this is a fixed requirement\n"
                "🛒 No minimum quantity required after the first order, *except*:\n"
                "🔑 **Lethal Keys** require a **minimum of 10 units per order**\n"
                "🤑 Enjoy a **25% discount** on all products\n"
                "🎉 **After some time**, you’ll unlock an even bigger **30% discount**, "
                "and with selected providers, savings can go up to **35%–40%**!\n"
                "### 💳 **Payments accepted via cryptocurrency only** (e.g., USDT, BTC)\n"
                "### ❌ **No credit card resellers** allowed\n\n"
                "## You’ll also get access to a **Reseller Panel** to instantly order keys with ease.\n\n"
                "If you have any questions, feel free to reach out – we're here to help!"
            ),
            color=0xee00a2,
        )
        embed.set_footer(text="Official Reseller Program – Cheats.Love")
        await interaction.response.send_message(embed=embed)

    # 📌 Winver

    @app_commands.command(name="winver", description="Instructs the user to check their Windows version.")
    async def winver(self, interaction: discord.Interaction):
        if not any(role.id in admin_role_ids for role in interaction.user.roles):
            await interaction.response.send_message(
                "🚫 You are not authorized to use this command.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Check Your Windows Version 🖥️",
            description="Please enter `winver` into your **Windows search bar**, and send us a screenshot showing your Windows version.",
            color=0xee00a2,
        )
        embed.set_footer(text="This helps us assist you better. Thank you!")

        await interaction.response.send_message(embed=embed)

    # 📌 Verify
    @app_commands.command(name="verify", description="Sends a verification reminder message.")
    async def verify(self, interaction: discord.Interaction):
        if not any(role.id in admin_role_ids for role in interaction.user.roles):
            await interaction.response.send_message(
                "🚫 You are not authorized to use this command.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🔐 Verify Yourself",
            description="Please use the channel <#1142773089063682058> to verify and get access to the whole Discord Community.",
            color=0xee00a2,
        )
        embed.set_footer(text="Thank you for joining us!")

        await interaction.response.send_message(embed=embed)

   # Slash Command
    @app_commands.command(name="troubleshoot", description="Start a troubleshooting process for a product")
    @app_commands.describe(product_name="Select a product to troubleshoot")
    async def troubleshoot(self, interaction: discord.Interaction, product_name: str):
        # Role check
        if not any(role.id in admin_role_ids + ticket_viewer_role_ids for role in interaction.user.roles):
            await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
            return

        troubleshoot_data = load_troubleshoot_data()

        if product_name not in troubleshoot_data:
            await interaction.response.send_message(f"❌ No troubleshooting data found for '{product_name}'.", ephemeral=True)
            return

        product = troubleshoot_data[product_name]

        embed = discord.Embed(
            title=f"Troubleshooting: {product['name']}",
            description="Have you used this product before?",
            color=EMBED_COLOR
        )

        view = discord.ui.View(timeout=None)

        # ✅ Yes button
        yes_button = discord.ui.Button(
            label="Yes", style=discord.ButtonStyle.green)

        async def yes_callback(btn_interaction: discord.Interaction):
            if btn_interaction.user != interaction.user:
                await btn_interaction.response.send_message("This button is not for you.", ephemeral=True)
                return
            await self.send_already_used_troubleshoot(btn_interaction, product_name)

        yes_button.callback = yes_callback
        view.add_item(yes_button)

        # ❌ No button
        no_button = discord.ui.Button(
            label="No", style=discord.ButtonStyle.red)

        async def no_callback(btn_interaction: discord.Interaction):
            if btn_interaction.user != interaction.user:
                await btn_interaction.response.send_message("This button is not for you.", ephemeral=True)
                return
            await self.send_first_time_troubleshoot(btn_interaction, product_name)

        no_button.callback = no_callback
        view.add_item(no_button)

        await interaction.response.send_message(embed=embed, view=view)

    # 🔍 Autocomplete
    @troubleshoot.autocomplete("product_name")
    async def product_name_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=product, value=product)
            for product in PRODUCTS if current.lower() in product.lower()
        ]

    # 🟢 First-time user steps
    async def send_first_time_troubleshoot(self, interaction: discord.Interaction, product_name: str):
        troubleshoot_data = load_troubleshoot_data()
        product = troubleshoot_data[product_name]["first_time"]

        embed = discord.Embed(
            title=product["title"],
            description=product["description"],
            color=EMBED_COLOR
        )

        for step in product["steps"]:
            embed.add_field(name=step["title"],
                            value=step["description"], inline=False)

        embed.add_field(name="📺 Video Guide:",
                        value=f"[Watch here]({product['video']})", inline=False)

        await interaction.response.send_message(embed=embed)

    # 🔵 Already-used steps
    async def send_already_used_troubleshoot(self, interaction: discord.Interaction, product_name: str):
        troubleshoot_data = load_troubleshoot_data()
        product = troubleshoot_data[product_name]["already_used"]

        embed = discord.Embed(
            title=product["title"],
            color=EMBED_COLOR
        )

        for step in product["steps"]:
            embed.add_field(name=step["title"],
                            value=step["description"], inline=False)

        view = discord.ui.View(timeout=None)
        submit_button = discord.ui.Button(
            label="Submit Information", style=discord.ButtonStyle.blurple)

        async def submit_callback(btn_interaction: discord.Interaction):
            await btn_interaction.response.send_modal(SubmitDX11Modal(product_name))

        submit_button.callback = submit_callback
        view.add_item(submit_button)

        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Support(bot))


"""
@bot.tree.command(name="altpayment", description="Instructs the user how to provide payment proof.")
async def altpayment(interaction: discord.Interaction):
    if not any(role.id in admin_role_ids for role in interaction.user.roles):
        await interaction.response.send_message("🚫 You are not authorized to use this command.", ephemeral=True)
        return

    embed = discord.Embed(
        title="💳 Payment Instructions 💳",
        description=(
            "**1️⃣ Ensure the transaction is completed successfully.**\n"
            "**2️⃣ Provide a screenshot of the transaction details as proof of payment.**\n"
            "**3️⃣ Make sure the screenshot is clear and uncropped.**\n\n"
            "⚠️ **Rules for Payment** ⚠️\n"
            "- Payments must be sent as **Friends & Family (F&F)**.\n"
            "- Double-check the address before sending funds.\n"
            "- **All payments are non-refundable** in case of errors or incorrect transactions.\n"
            "- **Do NOT** include any notes or memos with the transaction.\n\n"
            "**Accepted Payment Methods:**\n"
            "📧 PayPal: `hhe8809@gmail.com`\n"
            "💵 CashApp: `$miner4hyre35`"
        ),
        color=0xee00a2
    )
    embed.set_footer(text="Official Alt-Payment Reseller ShmurdaTech")

    await interaction.response.send_message(embed=embed)
"""
