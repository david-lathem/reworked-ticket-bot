import discord
from discord.ext import commands, tasks
import asyncio
import random
import json
import os
from datetime import datetime, timedelta
import pytz

GIVEAWAY_FILE = 'data.json'
DEFAULT_EMOJI = ':cheatslove:'
TICKET_LINK = 'https://discord.com/channels/982654393839128677/993504317984215050'


def pad_embed_text(text, target_length=90):
    # Macht alle Texte etwa gleich lang, um konsistente Embed-Größe zu erzwingen
    raw = text.replace('\n', ' ')
    if len(raw) >= target_length:
        return text + "\n\u200b"
    else:
        padding = "\u200b" * (target_length - len(raw))
        return text + padding


reminder_times = [86400, 43200, 21600, 10800, 3600, 300]

reminder_templates = [
    "||@everyone|| Giveaway ends soon! Don't miss out!",
    "||@everyone|| Final countdown! Time is running out!",
    "||@everyone|| Only a bit left to join the giveaway!",
    "||@everyone|| Tick tock... Giveaway almost over!",
    "||@everyone|| This is your sign to react NOW!",
    "||@everyone|| You still have a chance to win – hurry up!",
    "||@everyone|| Last moments to grab the prize!",
    "||@everyone|| Still thinking? Time's almost up!",
    "||@everyone|| Almost done! React fast!",
    "||@everyone|| Better late than never – giveaway ending soon!",
]

finalist_messages = [
    "You're among the FINAL 10!", "Finalists have been chosen – it's getting serious!",
    "Top 10 selected!", "You've made it to the finals – hold on!",
    "Only 10 left standing!", "Finalist alert! You're still in!",
    "Down to the last 10!", "Survived the purge – top 10 baby!",
    "Final showdown begins now!", "From many to few – you made it!"
]

winner_messages = [
    "CONGRATS {user}, you secured {place} place and won **{prize}**!",
    "{user} just won {place} place! Prize: **{prize}**!",
    "{user} takes {place} place – enjoy your **{prize}**!",
    "Massive congrats {user}, you're our #{place} winner: **{prize}**!",
    "{user}, you're walking away with {prize} for {place} place!",
    "Everyone cheer for {user} – {place} place and a {prize} winner!",
    "{user} won {place} place in the giveaway! Prize: {prize}!",
    "{user} just grabbed {place} place and scored **{prize}**!",
    "Lucky {user}, {place} place is yours – enjoy your prize: {prize}!",
    "BOOM! {user} wins {place} place – prize: **{prize}**!",
]

pm_templates = [
    "Hey {user}! You're one of the giveaway winners – {place} place, winning **{prize}**! Please open {ticket} to claim your reward!",
    "Guess what {user}? You won {place} place and earned **{prize}**! Open {ticket} to receive your prize.",
    "{user}, congrats on {place} place! Your prize: **{prize}**! Claim it via {ticket} – we’re hyped for you!",
    "{user} – {place} place is YOURS! Claim your **{prize}** here: {ticket}.",
    "You did it, {user}! {place} place winner! Claim: {ticket} (you won {prize})",
    "Wooo! {user}, you're a winner! {place} place with **{prize}** – head to {ticket} to get it!",
    "Big win, {user}! You got {place} place! Grab your prize ({prize}) here: {ticket}",
    "{user}, check this out – you won! {place} place, {prize} is yours! Hit up {ticket} now!",
    "Let’s gooo! {user} = {place} place! Claim your reward here: {ticket} – prize: {prize}",
    "{user}, you're a legend! {place} place in the giveaway – prize: {prize}! Use {ticket} to get it."
]

EMBED_THUMBNAIL = "https://cdn.discordapp.com/attachments/997589100389486602/1364561961710260305/LogoTest8.png?ex=680a1edc&is=6808cd5c&hm=beab5430d62ba303000255a539d0a2415ac7687a2311df07cb58ed01c0b276de&"
EMBED_COLOR = 0xee00a2

active_giveaways = {}


async def send_embed_message(destination, content, *, title=None, footer=None):
    embed = discord.Embed(description=content, color=EMBED_COLOR)
    if title:
        embed.title = title
    if footer:
        embed.set_footer(text=footer)
    embed.set_thumbnail(url=EMBED_THUMBNAIL)
    await destination.send(embed=embed)


class Giveaway:
    def __init__(self, ctx, prizes, end_time, emoji, target_channel, booster_only=False):
        self.ctx = ctx
        self.channel = target_channel
        self.guild = ctx.guild
        self.prizes = prizes
        self.end_time = end_time
        self.emoji = emoji or DEFAULT_EMOJI
        self.message = None
        self.reminder_msgs = []
        self.ended = False
        self.booster_only = booster_only

    async def start(self):
        prize_lines = [f"🥇 1st Place: {self.prizes[0]}"]
        if len(self.prizes) > 1:
            prize_lines.append(f"🥈 2nd Place: {self.prizes[1]}")
        if len(self.prizes) > 2:
            prize_lines.append(f"🥉 3rd Place: {self.prizes[2]}")

        if self.booster_only:
            embed = discord.Embed(
                title="🚀 Boosters Only Giveaway!",
                description=f"React with {self.emoji} to enter!\n\n" +
                "\n".join(prize_lines) + "\n\n||@everyone||",
                color=EMBED_COLOR
            )
        else:
            embed = discord.Embed(
                title="🎁 Giveaway Time!",
                description=f"React with {self.emoji} to enter!\n\n" +
                "\n".join(prize_lines) + "\n\n||@everyone||",
                color=EMBED_COLOR
            )
        embed.set_footer(
            text=f"Ends: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')} (Server Time)")
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        self.message = await self.channel.send(embed=embed)
        await self.message.add_reaction(self.emoji)
        self.schedule_reminders()

    def schedule_reminders(self):
        now = datetime.now()
        for t in reminder_times:
            reminder_at = self.end_time - timedelta(seconds=t)
            if reminder_at > now:
                delay = (reminder_at - now).total_seconds()
                asyncio.get_event_loop().call_later(
                    delay, lambda t=t: asyncio.create_task(self.send_reminder(t)))

    async def send_reminder(self, seconds_left):
        for msg in self.reminder_msgs:
            try:
                await msg.delete()
            except:
                pass

        minutes = int(seconds_left / 60)
        hours = minutes // 60
        remaining_minutes = minutes % 60

        # Nicely formatted time string
        if hours > 0:
            hour_str = f"{hours} hour" if hours == 1 else f"{hours} hours"
            minute_str = f"{remaining_minutes} minute" if remaining_minutes == 1 else f"{remaining_minutes} minutes"
            if remaining_minutes > 0:
                time_str = f"{hour_str} {minute_str}"
            else:
                time_str = hour_str
        else:
            time_str = f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"

        text = random.choice(reminder_templates)
        embed = discord.Embed(
            description=f"**{text}** ({time_str} left!)\n\u200b",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=EMBED_THUMBNAIL)
        embed.set_footer(
            text=f"Ends: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')} (Server Time)")
        msg = await self.channel.send(embed=embed)
        self.reminder_msgs.append(msg)

    async def end(self):
        if self.ended:
            return
        self.ended = True
        msg = await self.channel.fetch_message(self.message.id)
        reaction = next((r for r in msg.reactions if str(
            r.emoji) == str(self.emoji)), None)
        if reaction is None:
            await send_embed_message(self.channel, "No valid reaction found. Giveaway could not be completed.", title="❌ Giveaway Error")
            return

        users = [u async for u in reaction.users() if not u.bot]

        if self.booster_only:
            booster_role = self.guild.get_role(1143187882694168666)
            if booster_role:
                users = [u for u in users if isinstance(
                    u, discord.Member) and booster_role in u.roles]
                if not users:
                    await send_embed_message(self.channel, "No eligible booster participants. Giveaway ended with no winner.", title="😢 No Eligible Participants")
                    return

        if not users:
            await send_embed_message(self.channel, "No one participated in the giveaway.", title="😢 No Participants")
            return
        random.shuffle(users)
        finalists = users[:10] if len(users) >= 10 else users
        finalist_embed = discord.Embed(
            title="🎉 Finalists Selected!",
            description="\n".join(u.mention for u in finalists),
            color=EMBED_COLOR
        )
        finalist_embed.set_footer(text=random.choice(finalist_messages))
        finalist_embed.set_thumbnail(url=EMBED_THUMBNAIL)
        await self.channel.send(embed=finalist_embed)
        winners = random.sample(finalists, min(
            len(finalists), len(self.prizes)))
        places = ['1st', '2nd', '3rd']
        for i, user in enumerate(winners):
            place = places[i]
            prize_text = self.prizes[i]
            msg = random.choice(winner_messages).format(
                user=user.mention, place=place, prize=prize_text)
            await send_embed_message(self.channel, pad_embed_text(msg), title=f"🏆 {place.capitalize()} Place Winner!")
            # await send_embed_message(self.channel, msg, title=f"🏆 {place.capitalize()} Place Winner!")
            dm_msg = random.choice(pm_templates).format(
                user=user.name, place=place, prize=prize_text, ticket=TICKET_LINK)
            dm_embed = discord.Embed(
                title="🎁 You Won a Giveaway!", description=dm_msg, color=EMBED_COLOR)
            dm_embed.set_footer(text="Claim your prize soon!")
            dm_embed.set_thumbnail(url=EMBED_THUMBNAIL)
            try:
                await user.send(embed=dm_embed)
            except:
                print(f"Couldn't DM a winner {user.mention}")
                # await send_embed_message(self.channel, f"Couldn't DM {user.mention} – please contact support!", title="⚠️ DM Failed")
        del active_giveaways[self.channel.id]
        self.save()

    def to_dict(self):
        return {
            'channel': self.channel.id,
            'prizes': self.prizes,
            'end_time': self.end_time.isoformat(),
            'emoji': self.emoji,
            'message': self.message.id if self.message else None,
            'booster_only': self.booster_only
        }

    def save(self):
        data = {str(k): v.to_dict() for k, v in active_giveaways.items()}
        with open(GIVEAWAY_FILE, 'w') as f:
            json.dump(data, f, indent=2)


async def load_giveaways(bot):
    if not os.path.exists(GIVEAWAY_FILE):
        return
    with open(GIVEAWAY_FILE) as f:
        data = json.load(f)
    for cid, g in data.items():
        channel = bot.get_channel(int(g['channel']))
        if not channel:
            continue
        ctx = type('obj', (object,), {
                   'channel': channel, 'guild': channel.guild})
        end_time = datetime.fromisoformat(g['end_time'])
        g_obj = Giveaway(
            ctx,
            g['prizes'],
            end_time,
            g['emoji'],
            channel,
            g.get('booster_only', False)  # 🔸 NEU
        )
        try:
            g_obj.message = await channel.fetch_message(g['message'])
        except:
            continue
        active_giveaways[int(cid)] = g_obj
        asyncio.create_task(schedule_giveaway_end(g_obj))


async def schedule_giveaway_end(g_obj):
    delay = (g_obj.end_time - datetime.now()).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    await g_obj.end()


def setup(bot):
    @bot.command()
    async def giveaway1(ctx):
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        await send_embed_message(ctx, "How many winners (max 3)?")
        winner_count = int((await ctx.bot.wait_for('message', check=check)).content)
        prizes = []
        for i in range(winner_count):
            await send_embed_message(ctx, f"Enter the prize for place {i+1}:")
            prize = (await ctx.bot.wait_for('message', check=check)).content
            prizes.append(prize)
        await send_embed_message(ctx, "Enter end date & time (Server Time) [YYYY-MM-DD HH:MM]:")
        raw_end = (await ctx.bot.wait_for('message', check=check)).content
        end_time = datetime.strptime(raw_end, '%Y-%m-%d %H:%M')
        await send_embed_message(ctx, f"React emoji? (Press enter to use default {DEFAULT_EMOJI})")
        emoji_msg = await ctx.bot.wait_for('message', check=check)
        emoji = emoji_msg.content if emoji_msg.content else DEFAULT_EMOJI
        await send_embed_message(ctx, "Booster only? (yes/no)")
        booster_response = (await ctx.bot.wait_for('message', check=check)).content.lower()
        booster_only = booster_response in ['yes', 'y', 'true', '1']
        await send_embed_message(ctx, "Enter the channel ID where the giveaway should be posted:")
        channel_id = int((await ctx.bot.wait_for('message', check=check)).content)
        target_channel = ctx.bot.get_channel(channel_id)
        if not target_channel:
            await send_embed_message(ctx, "❌ Invalid channel ID. Aborting.", title="Error")
            return
        g = Giveaway(ctx, prizes, end_time, emoji,
                     target_channel, booster_only=booster_only)
        await g.start()
        active_giveaways[target_channel.id] = g
        g.save()
        asyncio.create_task(schedule_giveaway_end(g))
