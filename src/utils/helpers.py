from datetime import datetime, timedelta
import asyncio

from utils.files import load_tickets, load_renames, save_renames, save_tickets
from utils.constants import MAX_RENAMES, TIME_WINDOW


async def _delayed_rename(channel, new_name, delay_seconds):
    await asyncio.sleep(delay_seconds)
    try:
        await channel.edit(name=new_name)
        print(f"[Delayed Rename] {channel.id} → {new_name}")
    except Exception as e:
        print(f"[Delayed Rename Error] {e}")


async def safe_enqueue_rename(channel, new_name):
    now = datetime.utcnow()
    tickets = load_tickets()
    renames = load_renames()

    # Key bleibt weiterhin channel.name für tickets.json
    channel_key = channel.name
    channel_id = str(channel.id)

    # Sicherstellen, dass der Tickets-Eintrag vorhanden ist
    data = tickets.get(channel_key)
    if data is None:
        data = {"channel_id": channel_id}
        tickets[channel_key] = data

    # Sicherstellen, dass die Channel-ID immer mitgespeichert ist
    data["channel_id"] = channel_id

    # Hole die Rename-History aus der separaten Datei
    rename_data = renames.setdefault(channel_id, {})
    ts_list = rename_data.get("timestamps", [])
    parsed = [datetime.fromisoformat(ts) for ts in ts_list]
    recent = [ts for ts in parsed if now - ts < TIME_WINDOW]

    if len(recent) < MAX_RENAMES:
        # ✅ Sofort umbenennen
        try:
            await channel.edit(name=new_name)
            print(f"[Immediate Rename] {channel.name} → {new_name}")
        except Exception as e:
            print(f"[Immediate Rename Error] {e}")

        # Timestamp anhängen und speichern
        parsed.append(now)
        rename_data["timestamps"] = [ts.isoformat() for ts in parsed]
        renames[channel_id] = rename_data
        save_renames(renames)

        # Tickets aktualisieren, falls sich der Name geändert hat
        if new_name != channel_key:
            tickets[new_name] = data
            del tickets[channel_key]
        save_tickets(tickets)
        return True

    else:
        # 🕒 Delay berechnen
        earliest = min(recent)
        next_allowed = earliest + TIME_WINDOW
        delay = max((next_allowed - now).total_seconds(), 0) + 1
        scheduled_ts = now + timedelta(seconds=delay)

        # Geplanten Timestamp vormerken
        parsed.append(scheduled_ts)
        rename_data["timestamps"] = [ts.isoformat() for ts in parsed]
        renames[channel_id] = rename_data
        save_renames(renames)

        # Tickets aktualisieren, falls sich der Name geändert hat
        if new_name != channel_key:
            tickets[new_name] = data
            del tickets[channel_key]
        save_tickets(tickets)

        asyncio.create_task(_delayed_rename(channel, new_name, delay))
        print(
            f"[Queued Rename] {channel.name} → {new_name} in {round(delay)}s")
        return False


def update_last_message(channel_name):  # <-- channel_name statt channel_id
    tickets = load_tickets()
    if channel_name in tickets:
        tickets[channel_name]["last_message"] = datetime.utcnow().isoformat()
        tickets[channel_name]["warned"] = False
        save_tickets(tickets)
