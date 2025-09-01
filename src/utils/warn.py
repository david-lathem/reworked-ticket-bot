import discord
from datetime import datetime, timedelta
import asyncio

from utils.files import load_warnings, save_warnings, config


async def apply_warning(
    bot,
    user: discord.Member,
    reason: str,
    channel: discord.abc.Messageable = None,
    issuer: discord.Member = None,
    original_message: str = None  # <-- Neuer Parameter für den Logs-Inhalt,
):
    warnings = load_warnings()
    user_id = str(user.id)
    if user_id not in warnings:
        warnings[user_id] = []

    warn_count = len(warnings[user_id]) + 1
    # 1min, 5min, 30min, 1h, 2h
    timeout_durations = [60, 300, 1800, 3600, 7200]
    timeout = timeout_durations[min(
        warn_count - 1, len(timeout_durations) - 1)]

    warnings[user_id].append({
        "reason": reason,
        "timeout": timeout,
        "expires": True
    })
    save_warnings(warnings)

    end_time = discord.utils.utcnow() + timedelta(seconds=timeout)
    try:
        await user.timeout(end_time, reason=f"Warning {warn_count}/5: {reason}")
    except discord.Forbidden:
        pass

    color_code = 0xee00a2
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- EMBED für Logs-Kanal ---
    log_embed = discord.Embed(
        title=f"User Warned - {warn_count}/5",
        description=(
            f"**User:** {user.mention}\n"
            f"**Issuer:** {issuer.mention if issuer else 'System'}\n"
            f"**Reason:** {reason}\n"
            f"**New Warning Count:** {warn_count}\n"
            f"**Timeout:** {timeout // 60} minutes"
        ),
        color=color_code
    )
    log_embed.set_footer(text=f"Cheats.Love - {now_str}")

    # Falls der User 5 Warnungen erreicht hat, passe den Titel an
    if warn_count >= 5:
        log_embed.title = f"🚨 {user.display_name} reached {warn_count}/5 warnings!"
        log_embed.description += "\n## **Possible community ban.**"

    # Nur im Logs-Embed => Originalnachricht
    if original_message:
        truncated_msg = (
            original_message[:1000] + "...") if len(original_message) > 1000 else original_message
        log_embed.add_field(name="Original Message",
                            value=truncated_msg, inline=False)

    log_channel_id = config.get("log_channel_id")
    if log_channel_id:
        logs_channel = bot.get_channel(log_channel_id)
        if logs_channel:
            await logs_channel.send(embed=log_embed)

    # --- EMBED für die DM an den User ---
    dm_embed = discord.Embed(
        title=f"Warning {warn_count}/5",
        description=(
            f"You have been muted for **{timeout // 60} minutes** "
            f"due to: **{reason}**.\n\n"
            f"Total warnings: {warn_count}/5."
        ),
        color=color_code
    )
    dm_embed.set_footer(text=f"Cheats.Love - {now_str}")

    try:
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        pass


async def clear_warnings():
    while True:
        await asyncio.sleep(86400)  # 24h
        warnings = load_warnings()
        for user_id in list(warnings.keys()):
            new_warnings = [w for w in warnings[user_id] if not w["expires"]]
            warnings[user_id] = new_warnings
            if not warnings[user_id]:
                del warnings[user_id]
        save_warnings(warnings)
