async def generate_transcript(channel):
    """Generate a detailed transcript of the channel, including embeds."""
    transcript = []
    try:
        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author = f"{message.author.name}#{message.author.discriminator}"

            content = message.content if message.content else "[No Text Content]"
            attachments = "\n".join(
                [attachment.url for attachment in message.attachments]) if message.attachments else ""

            message_entry = f"[{timestamp}] {author}: {content}"
            if attachments:
                message_entry += f"\nAttachments: {attachments}"

            if message.embeds:
                for embed in message.embeds:
                    embed_content = "\n--- EMBED ---\n"
                    if embed.title:
                        embed_content += f"Title: {embed.title}\n"
                    if embed.description:
                        embed_content += f"Description: {embed.description}\n"
                    if embed.fields:
                        for field in embed.fields:
                            embed_content += f"{field.name}: {field.value}\n"
                    if embed.footer and embed.footer.text:
                        embed_content += f"Footer: {embed.footer.text}\n"
                    if embed.author and embed.author.name:
                        embed_content += f"Author: {embed.author.name}\n"
                    embed_content += "--- END EMBED ---"
                    message_entry += f"\n{embed_content}"

            transcript.append(message_entry)

        if not transcript:
            transcript.append("[No messages found in this channel]")

        file_name = f"transcript-{channel.name}.txt"
        content_to_write = "\n\n".join(transcript)

        print("Writing the following content to the file:")
        print(content_to_write)

        with open(file_name, "w", encoding="utf-8") as f:
            f.write(content_to_write)

        print(f"Transcript successfully created: {file_name}")
        return file_name

    except Exception as e:
        print(f"Error generating transcript: {e}")
        return None
