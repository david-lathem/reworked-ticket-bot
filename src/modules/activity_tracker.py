import discord
from discord.ext import tasks
import datetime
import json
import os


def setup(bot):
    tracker = ActivityTracker(bot)
    tracker.start()


class ActivityTracker:
    def __init__(self, bot):
        self.bot = bot
        self.filename = "user_activity.json"

    def start(self):
        self.track_status.start()

    @tasks.loop(minutes=30)
    async def track_status(self):
        guild = discord.utils.get(self.bot.guilds)
        if guild is None:
            return

        status_count = {"online": 0, "idle": 0, "dnd": 0, "offline": 0}
        for member in guild.members:
            if member.bot:
                continue
            status = str(member.status)
            if status in status_count:
                status_count[status] += 1

        now = datetime.datetime.utcnow().isoformat()

        data = self.load_data()
        data[now] = status_count
        self.save_data(data)

    def load_data(self):
        if not os.path.exists(self.filename):
            return {}
        with open(self.filename, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def save_data(self, data):
        with open(self.filename, "w") as f:
            json.dump(data, f, indent=2)

    @track_status.before_loop
    async def before_tracking(self):
        await self.bot.wait_until_ready()
