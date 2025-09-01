from utils.files import config

admin_role_ids = config["admin_role_ids"]
ticket_viewer_role_ids = config["ticket_viewer_role_ids"]


def is_admin(obj):
    # Für klassische Commands
    if hasattr(obj, "author"):
        return any(role.id in admin_role_ids for role in obj.author.roles)
    # Für Slash Commands
    if hasattr(obj, "user"):
        return any(role.id in admin_role_ids for role in obj.user.roles)
    return False


def is_whitelisted_admin(obj):  # error1337
    # Für klassische Commands
    if hasattr(obj, "author"):
        return any(role.id in ticket_viewer_role_ids for role in obj.author.roles)
    # Für Slash Commands
    if hasattr(obj, "user"):
        return any(role.id in ticket_viewer_role_ids for role in obj.user.roles)
    return False
