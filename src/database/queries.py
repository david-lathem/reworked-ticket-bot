
def save_ticket_to_mysql(channel_name, creator_id, ticket_number, bot):
    """Insert a new ticket into MySQL."""
    query = """
    INSERT INTO tickets (discord_channel_id, creator_id, ticket_number)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE creator_id = %s;
    """
    bot.db.execute_query(
        query, (channel_name, creator_id, ticket_number, creator_id))


def close_ticket_in_mysql(channel_name, closed_by, closed_by_id, bot):  # ADD REASOn
    """Schließt das Ticket in MySQL und aktualisiert die Statistik."""

    # Überprüfen, ob das Ticket existiert
    check_query = "SELECT id FROM tickets WHERE discord_channel_id = %s"
    result = bot.db.execute_query(check_query, (channel_name,), fetch=True)

    if not result:
        print(f"🚨 ERROR: Kein Ticket in MySQL für {channel_name} gefunden!")
        return

    ticket_id = result[0]['id']

    # Ticket als geschlossen markieren
    query = """
    UPDATE tickets
    SET closed_by = %s, closed_at = NOW()
    WHERE id = %s;
    """
    bot.db.execute_query(query, (closed_by, ticket_id))
    print(f"✅ Ticket {ticket_id} wurde erfolgreich geschlossen!")

    # Statistik für den Supporter aktualisieren
    query_stats = """
    INSERT INTO ticket_statistics (support_id, tickets_closed, period)
    VALUES (%s, 1, 'daily')
    ON DUPLICATE KEY UPDATE tickets_closed = tickets_closed + 1;
    """
    bot.db.execute_query(query_stats, (closed_by_id,))


def save_message_to_mysql(channel_name, author_id, author_name, message_content, bot):
    """Insert a message into MySQL. Falls das Ticket fehlt, wird es hinzugefügt."""
    # Prüfe, ob das Ticket existiert
    check_ticket_query = "SELECT id FROM tickets WHERE discord_channel_id = %s"
    ticket_result = bot.db.execute_query(
        check_ticket_query, (channel_name,), fetch=True)

    if not ticket_result:
        print(
            f"🚨 ERROR: No ticket found for {channel_name}! Ticket will be created by the system now!")
        # Ticket automatisch hinzufügen
        create_ticket_query = """
        INSERT INTO tickets (discord_channel_id, creator_id, ticket_number)
        VALUES (%s, %s, %s)
        """
        bot.db.execute_query(create_ticket_query,
                             (channel_name, author_id, f"{channel_name}"))

        # Ticket-ID erneut abrufen
        ticket_result = bot.db.execute_query(
            check_ticket_query, (channel_name,), fetch=True)

    ticket_id = ticket_result[0]['id']
    print(f"✅ Ticket found! ID: {ticket_id}")

    # Füge die Nachricht ein (mit `author_name`)
    insert_query = """
    INSERT INTO ticket_messages (ticket_id, author_id, author_name, message)
    VALUES (%s, %s, %s, %s);
    """
    bot.db.execute_query(insert_query, (ticket_id, author_id,
                                        author_name, message_content))
