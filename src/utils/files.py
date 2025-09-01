import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(
    __file__), "..", '..', 'config', "config.json")

TICKETS_FILE = os.path.join(os.path.dirname(
    __file__), "..", '..', 'config', "tickets.json")
RENAME_FILE = os.path.join(os.path.dirname(
    __file__), "..", '..', 'config', "renames.json")
TROUBLESHOOT_FILE = os.path.join(os.path.dirname(
    __file__), "..", '..', 'config', "troubleshoot.json")
BOOSTER_CHANNELS_FILE = os.path.join(os.path.dirname(
    __file__), "..", '..', 'config', "booster_channels.json")
WARNINGS_FILE = os.path.join(os.path.dirname(
    __file__), "..", '..', 'config', "warnings.json")
SHADOWBAN_FILE = os.path.join(os.path.dirname(
    __file__), "..", '..', 'config', "shadowbans.json")

# Load once at startup
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

# Variables
ticket_counter_raw = config.get("ticket_counter", "0001")  # Default to "0001"
ticket_counter = int(ticket_counter_raw)  # Convert to integer for internal use
tickettool_channel_id = config.get("tickettool_channel_id", None)
supporter_emojis = config.get("supporter_emojis", {})


def load_config():
    """Reload config from disk"""
    global config
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    return config


def save_config(config):
    # Format the ticket counter as a string with leading zero if < 1000
    formatted_counter = f"{ticket_counter:04}" if ticket_counter < 1000 else str(
        ticket_counter)
    config["ticket_counter"] = formatted_counter
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def load_tickets():
    try:
        with open(TICKETS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def save_tickets(tickets):
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=4)


def load_renames():
    if not os.path.exists(RENAME_FILE):
        return {}
    with open(RENAME_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_renames(data):
    with open(RENAME_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_emojis():
    global supporter_emojis
    config["supporter_emojis"] = supporter_emojis
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def load_troubleshoot_data():
    with open(TROUBLESHOOT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def load_booster_channels():
    try:
        with open(BOOSTER_CHANNELS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_booster_channels(data):
    with open(BOOSTER_CHANNELS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_warnings():
    try:
        with open(WARNINGS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_warnings(data):
    with open(WARNINGS_FILE, "w") as file:
        json.dump(data, file, indent=4)


def load_shadowbans():
    try:
        with open(SHADOWBAN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"shadowbans": []}


def save_shadowbans(data):
    with open(SHADOWBAN_FILE, "w") as f:
        json.dump(data, f, indent=4)


def set_tickettool_channel_id(channel_id: int):
    global tickettool_channel_id
    tickettool_channel_id = channel_id


def set_supporter_emoji(user_id: str, emoji: str):
    global supporter_emojis
    supporter_emojis[user_id] = emoji


def set_ticket_counter(counter: int):
    global ticket_counter
    ticket_counter += counter
