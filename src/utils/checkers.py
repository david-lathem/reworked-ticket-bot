import discord
from datetime import datetime
import asyncio

from utils.files import load_tickets, save_tickets, load_booster_channels, save_booster_channels
from utils.constants import EMBED_COLOR, INACTIVITY_CLOSE_TIME, INACTIVITY_WARNING_TIME


async def check_inactive_tickets_once(bot):
    """
    Führt genau EINMAL die Inaktivitätsprüfung durch:
    - Schickt 12h/24h-Warnungen
    - Löscht verwaiste Tickets aus tickets.json
    """
    tickets = load_tickets()
    now = datetime.utcnow()
    tickets_to_delete = []

    for channel_id, data in tickets.items():
        last_message = data.get("last_message")
        creator_id = data.get("creator_id")
        warned = data.get("warned", False)
        warned_twice = data.get("warned_twice", False)

        if not last_message:
            continue

        try:
            last_time = datetime.fromisoformat(last_message)
            elapsed = now - last_time

            # channel_id ist der Ticket-Name (z.B. "ticket-0001")
            channel = discord.utils.get(
                bot.get_all_channels(), name=channel_id)
            if not channel:
                print(
                    f"[Cleanup] Channel {channel_id} not found, removing from tickets.json")
                tickets_to_delete.append(channel_id)
                continue

            # Erste Warnung nach 12h
            if elapsed >= INACTIVITY_WARNING_TIME and not warned:
                embed = discord.Embed(
                    title="⏳ Ticket Inactive",
                    description="This ticket has been inactive for 12 hours. "
                                "If there's no response within the next 12 hours, "
                                "it may be closed by the staff.",
                    color=EMBED_COLOR
                )
                if creator_id:
                    await channel.send(content=f"<@{creator_id}>", embed=embed)
                else:
                    await channel.send(embed=embed)
                    await asyncio.sleep(0.2)
                tickets[channel_id]["warned"] = True

            # Zweite Erinnerung nach 24h
            elif elapsed >= INACTIVITY_CLOSE_TIME and warned and not warned_twice:
                embed = discord.Embed(
                    title="📌 Ticket Still Inactive",
                    description="This ticket has been inactive for 24 hours. "
                                "Staff may now close this ticket at their discretion.",
                    color=EMBED_COLOR
                )
                await channel.send(embed=embed)
                await asyncio.sleep(0.2)
                tickets[channel_id]["warned_twice"] = True

        except Exception as ticket_error:
            print(
                f"[Error] While checking ticket {channel_id}: {ticket_error}")

    # Verwaiste Tickets entfernen
    for cid in tickets_to_delete:
        tickets.pop(cid, None)

    save_tickets(tickets)


async def check_booster_channels(bot):
    """Periodically check all booster-created voice channels, deleting any that are empty."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        booster_channels = load_booster_channels()
        for channel_id_str in list(booster_channels.keys()):
            channel_id = int(channel_id_str)
            vchannel = bot.get_channel(channel_id)

            if vchannel is None:
                booster_channels.pop(channel_id_str, None)
                save_booster_channels(booster_channels)
                continue

            if isinstance(vchannel, discord.VoiceChannel):
                if len(vchannel.members) == 0:
                    print(
                        f"Deleting empty booster channel: {vchannel.name} (ID: {vchannel.id})")
                    await vchannel.delete(reason="Empty booster channel cleanup.")
                    await asyncio.sleep(0.1)
                    booster_channels.pop(channel_id_str, None)
                    save_booster_channels(booster_channels)
        await asyncio.sleep(10*60)  # 10 minutes


async def reset_ticket_statistics(bot):
    """Tägliche & monatliche Statistiken updaten, plus lastmonth→total."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()

        # nur um Mitternacht UTC ausführen
        if now.hour == 0 and now.minute == 0:

            # 1) daily → weekly
            bot.db.execute_query("""
            INSERT INTO ticket_statistics (support_id, tickets_closed, period)
            SELECT support_id, tickets_closed, 'weekly'
            FROM ticket_statistics
            WHERE period = 'daily'
            ON DUPLICATE KEY
              UPDATE tickets_closed = ticket_statistics.tickets_closed + VALUES(tickets_closed);
            """)

            # 2) daily → monthly
            bot.db.execute_query("""
            INSERT INTO ticket_statistics (support_id, tickets_closed, period)
            SELECT support_id, tickets_closed, 'monthly'
            FROM ticket_statistics
            WHERE period = 'daily'
            ON DUPLICATE KEY
              UPDATE tickets_closed = ticket_statistics.tickets_closed + VALUES(tickets_closed);
            """)

            # 3) daily resetten
            bot.db.execute_query("""
            UPDATE ticket_statistics
            SET tickets_closed = 0, last_updated = NOW()
            WHERE period = 'daily';
            """)

            # 4) am 1. des Monats: monthly→lastmonth, lastmonth→total, dann Resets
            if now.day == 1:
                # 4a) monthly → lastmonth
                bot.db.execute_query("""
                INSERT INTO ticket_statistics (support_id, tickets_closed, period)
                SELECT support_id, tickets_closed, 'lastmonth'
                FROM ticket_statistics
                WHERE period = 'monthly'
                ON DUPLICATE KEY
                  UPDATE tickets_closed = VALUES(tickets_closed);
                """)

                # 4b) lastmonth → total
                bot.db.execute_query("""
                INSERT INTO ticket_statistics (support_id, tickets_closed, period)
                SELECT support_id, tickets_closed, 'total'
                FROM ticket_statistics
                WHERE period = 'lastmonth'
                ON DUPLICATE KEY
                  UPDATE tickets_closed = ticket_statistics.tickets_closed + VALUES(tickets_closed);
                """)

                # 4c) weekly, monthly und lastmonth resetten
                bot.db.execute_query("""
                UPDATE ticket_statistics
                SET tickets_closed = 0
                WHERE period IN ('weekly','monthly','lastmonth');
                """)

                print(
                    "✅ lastmonth→total verschoben und weekly/monthly/lastmonth zurückgesetzt.")

            print("✅ Daily→Weekly/Monthly übertragen und daily zurückgesetzt.")
            # für 60 Sekunden pausieren, damit der Block nur einmal pro Mitternacht läuft
            await asyncio.sleep(61)

        # sonst jede Minute nochmal prüfen
        await asyncio.sleep(60)
