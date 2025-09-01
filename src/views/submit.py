import discord

from utils.constants import EMBED_COLOR


class SubmitDX11Modal(discord.ui.Modal):
    """Modal für die Einreichung von DX11 Informationen."""

    def __init__(self, product_name):
        super().__init__(title="Submit DX11 Information")
        self.product_name = product_name

        self.key = discord.ui.TextInput(
            label="Key", placeholder="Enter your key", required=True)
        self.google_drive_link = discord.ui.TextInput(
            label="Google Drive Link", placeholder="Paste your DX11 link", required=True)
        self.problem_description = discord.ui.TextInput(label="Exact Problem Description", style=discord.TextStyle.paragraph,
                                                        placeholder="Describe your issue in detail (include error messages, steps tried)", required=True)

        self.add_item(self.key)
        self.add_item(self.google_drive_link)
        self.add_item(self.problem_description)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"Submission for {self.product_name}",
            color=EMBED_COLOR
        )
        embed.add_field(name="Key", value=self.key.value, inline=False)
        embed.add_field(name="Google Drive Link",
                        value=self.google_drive_link.value, inline=False)
        embed.add_field(name="Exact Problem Description",
                        value=self.problem_description.value, inline=False)
        embed.set_footer(
            text="The file is now under review. This may take up to 24 hours. Be prepared for an AnyDesk session if required. The time will be compensated.")

        await interaction.response.send_message("✅ Submission received! Your file will be reviewed soon.", ephemeral=True)
        await interaction.channel.send(embed=embed)
