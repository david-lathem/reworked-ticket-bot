import discord
from discord.ext import commands

from utils.access import is_admin
from utils.constants import EMBED_COLOR


class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="recalculate_stats")
    async def recalculate_stats(self, ctx):
        """Manually triggers weekly and monthly ticket stats aggregation based on daily data."""
        if not is_admin(ctx):
            await ctx.send("🚫 You are not authorized to use this command.")
            return

        # Weekly aggregation: last 7 days
        aggregate_weekly = """
        INSERT INTO ticket_statistics (support_id, tickets_closed, period)
        SELECT support_id, SUM(tickets_closed), 'weekly'
        FROM ticket_statistics
        WHERE period = 'daily' AND last_updated >= CURDATE() - INTERVAL 7 DAY
        GROUP BY support_id
        ON DUPLICATE KEY UPDATE tickets_closed = VALUES(tickets_closed);
        """
        self.bot.db.execute_query(aggregate_weekly)

        # Monthly aggregation: current month
        aggregate_monthly = """
        INSERT INTO ticket_statistics (support_id, tickets_closed, period)
        SELECT support_id, SUM(tickets_closed), 'monthly'
        FROM ticket_statistics
        WHERE period = 'daily'
        AND MONTH(last_updated) = MONTH(CURDATE())
        AND YEAR(last_updated) = YEAR(CURDATE())
        GROUP BY support_id
        ON DUPLICATE KEY UPDATE tickets_closed = VALUES(tickets_closed);
        """
        self.bot.db.execute_query(aggregate_monthly)

        await ctx.send("✅ Weekly and monthly statistics have been successfully recalculated.")

    @commands.command(name="supportstats")
    async def supportstats(self, ctx, member: discord.Member = None):
        """Show all support stats (daily, weekly, monthly, total) for a specific user."""
        if not is_admin(ctx):
            await ctx.send("🚫 You are not authorized to use this command.")
            return

        if member is None:
            await ctx.send("❗ Usage: `.supportstats @User`")
            return

        user_id = member.id
        stats = {"daily": 0, "weekly": 0, "monthly": 0, "total": 0}

        # Fetch daily, weekly, monthly from ticket_statistics
        query = """
        SELECT period, tickets_closed
        FROM ticket_statistics
        WHERE support_id = %s AND period IN ('daily', 'weekly', 'monthly')
        """
        results = self.bot.db.execute_query(query, (user_id,), fetch=True)
        for row in results:
            stats[row["period"]] = row["tickets_closed"]

        # Calculate total based on all daily entries
        query_total = """
        SELECT SUM(tickets_closed) as total
        FROM ticket_statistics
        WHERE support_id = %s AND period = 'daily'
        """
        total_result = self.bot.db.execute_query(
            query_total, (user_id,), fetch=True)
        if total_result and total_result[0]["total"] is not None:
            stats["total"] = total_result[0]["total"]

        # Build and send embed
        embed = discord.Embed(
            title=f"📊 Support Stats for {member.display_name}",
            color=0xee00a2
        )
        embed.add_field(name="🕒 Daily", value=str(stats["daily"]), inline=True)
        embed.add_field(name="📆 Weekly", value=str(
            stats["weekly"]), inline=True)
        embed.add_field(name="🗓️ Monthly", value=str(
            stats["monthly"]), inline=True)
        embed.add_field(name="🌐 Total (all-time)",
                        value=str(stats["total"]), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="top_supporters")
    async def top_supporters(self, ctx, period: str = "daily"):
        """Show top 5 supporters for the specified period."""
        if not is_admin(ctx):
            return await ctx.send("🚫 You are not authorized to use this command.")

        period = period.lower()
        allowed = ["daily", "weekly", "monthly", "lastmonth", "total"]
        if period not in allowed:
            return await ctx.send("❌ Invalid period. Use `daily`, `weekly`, `monthly`, `lastmonth` or `total`.")

        if period == "total":
            query = "SELECT support_id, tickets_closed AS total FROM ticket_statistics WHERE period = 'total' ORDER BY total DESC LIMIT 5;"
        elif period == "lastmonth":
            query = "SELECT support_id, tickets_closed AS total FROM ticket_statistics WHERE period = 'lastmonth' ORDER BY total DESC LIMIT 5;"
        elif period == "monthly":
            query = """
            SELECT support_id, SUM(tickets_closed) AS total
            FROM ticket_statistics
            WHERE period = 'daily' AND last_updated >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
            GROUP BY support_id
            ORDER BY total DESC
            LIMIT 5;
            """
        elif period == "weekly":
            query = """
            SELECT support_id, SUM(tickets_closed) AS total
            FROM ticket_statistics
            WHERE period = 'daily' AND last_updated >= CURDATE() - INTERVAL 7 DAY
            GROUP BY support_id
            ORDER BY total DESC
            LIMIT 5;
            """
        else:  # daily
            query = "SELECT support_id, tickets_closed AS total FROM ticket_statistics WHERE period = 'daily' ORDER BY total DESC LIMIT 5;"

        results = self.bot.db.execute_query(query, fetch=True)
        if not results:
            return await ctx.send("📉 No statistics available for this period.")

        desc = "\n".join(
            f"👤 <@{r['support_id']}> – {r['total']} tickets" for r in results)
        embed = discord.Embed(title=f"🏆 Top Supporters ({period.capitalize()})",
                              description=desc,
                              color=EMBED_COLOR)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(StatsCog(bot))
