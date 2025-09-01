# src/main.py

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging

from database.db import Database


class TicketBot(commands.Bot):
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
        self.DISCORD_GUILD = int(os.getenv("DISCORD_GUILD"))
        self.MYSQL_HOST = os.getenv("MYSQL_HOST")
        self.MYSQL_USER = os.getenv("MYSQL_USER")
        self.MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        self.MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

        intents = discord.Intents.default()
        intents.messages = True
        intents.guilds = True
        intents.message_content = True
        intents.presences = True
        intents.members = True
        intents.reactions = True

        # Init DB
        self.db = Database(
            host=self.MYSQL_HOST,
            user=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            database=self.MYSQL_DATABASE
        )

        super().__init__(
            command_prefix=".",
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        """
        Called before the bot connects to Discord.
        Best place to load cogs/extensions.
        """
        await self.load_all_cogs()

    async def load_all_cogs(self):
        """Auto-load all cogs from cogs/ and events/"""
        for folder in ["commands", "events"]:
            folder_path = os.path.join("src", folder)
            if not os.path.exists(folder_path):
                continue

            for filename in os.listdir(folder_path):
                if filename.endswith(".py"):
                    extension = f"{folder}.{filename[:-3]}"
                    try:
                        await self.load_extension(extension)
                        print(f"✅ Loaded extension: {extension}")
                    except Exception as e:
                        logging.exception(e)


bot = TicketBot()
bot.run(bot.DISCORD_TOKEN)
