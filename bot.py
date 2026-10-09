import logging
import os
import re
import sqlite3
from functools import partial
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from openai import OpenAI


BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
NVIDIA_TIMEOUT_SECONDS = float(os.getenv("NVIDIA_TIMEOUT_SECONDS", "120"))
HISTORY_LIMIT = 10
DISCORD_MESSAGE_LIMIT = 1900
SYSTEM_PROMPT = (
    "You are a helpful, clear, and friendly assistant chatting in Discord. "
    "Keep replies concise unless the user asks for detail."
)
DATABASE_PATH = Path(
    os.getenv("CHAT_HISTORY_DB", str(Path(__file__).with_name("chat_history.db")))
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("disbot")


def init_db():
    """Create the conversation history table if it does not already exist."""
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_channel_id_id "
            "ON messages (channel_id, id)"
        )


def add_message_to_db(channel_id, role, content):
    """Persist one user or assistant message for a channel."""
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        connection.execute(
            "INSERT INTO messages (channel_id, role, content) VALUES (?, ?, ?)",
            (channel_id, role, content),
        )


def get_history_from_db(channel_id, limit=HISTORY_LIMIT):
    """Return the most recent messages in chronological order."""
    limit = max(0, int(limit))
    if limit == 0:
        return []

    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        rows = connection.execute(
            """
            SELECT role, content
            FROM messages
            WHERE channel_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (channel_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def clear_history_from_db(channel_id):
    """Delete all stored messages for a channel."""
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        connection.execute("DELETE FROM messages WHERE channel_id = ?", (channel_id,))


def chunk_message(text, limit=DISCORD_MESSAGE_LIMIT):
    """Split text into Discord-safe pieces, preferring paragraph or word breaks."""
    remaining = text.strip()
    chunks = []
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit + 1)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at < limit // 2:
            split_at = limit

        chunk = remaining[:split_at].rstrip()
        if not chunk:
            chunk = remaining[:limit]
            split_at = limit
        chunks.append(chunk)
        remaining = remaining[split_at:].lstrip()

    if remaining:
        chunks.append(remaining)
    return chunks


load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
MODEL = os.getenv("NVIDIA_MODEL", DEFAULT_MODEL)

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is required. Set it in the host environment or .env.")
if not NVIDIA_API_KEY:
    raise RuntimeError("NVIDIA_API_KEY is required. Set it in the host environment or .env.")

client = OpenAI(
    base_url=BASE_URL,
    api_key=NVIDIA_API_KEY,
    timeout=NVIDIA_TIMEOUT_SECONDS,
    max_retries=0,
)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
commands_synced = False


async def generate_response(channel_id, prompt):
    add_message_to_db(channel_id, "user", prompt)
    history = get_history_from_db(channel_id, HISTORY_LIMIT)
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history]
    request = partial(
        client.chat.completions.create,
        model=MODEL,
        messages=api_messages,
        temperature=0.7,
        max_tokens=1024,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )

    completion = await bot.loop.run_in_executor(None, request)
    response = completion.choices[0].message.content
    if not response or not response.strip():
        response = "I couldn't produce a response just now. Please try again."
    response = response.strip()
    add_message_to_db(channel_id, "assistant", response)
    return response


@bot.event
async def on_ready():
    global commands_synced
    logger.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    if not commands_synced:
        try:
            synced = await bot.tree.sync()
            commands_synced = True
            logger.info("Synced %s application command(s)", len(synced))
        except Exception:
            logger.exception("Failed to sync application commands")


@bot.command(name="reset")
async def reset_command(ctx):
    """Clear this channel's saved conversation history."""
    clear_history_from_db(ctx.channel.id)
    await ctx.send("Conversation history for this channel has been cleared.")


@bot.tree.command(name="ask", description="Ask the AI assistant a question")
@app_commands.describe(prompt="What would you like to ask?")
async def ask_command(interaction: discord.Interaction, prompt: str):
    """Answer a question using the channel's saved conversation history."""
    await interaction.response.defer(thinking=True)
    try:
        response = await generate_response(interaction.channel_id, prompt)
        for chunk in chunk_message(response):
            await interaction.followup.send(chunk)
    except Exception:
        logger.exception(
            "Failed to process /ask in channel %s", interaction.channel_id
        )
        await interaction.followup.send(
            "Sorry, I couldn't process that message right now. Please try again later."
        )


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)
    if message.content.startswith("!"):
        return

    if bot.user is None:
        return

    is_direct_message = message.guild is None
    is_mentioned = bot.user in message.mentions
    if not (is_direct_message or is_mentioned):
        return

    prompt = message.content
    mention_pattern = rf"<@!?{bot.user.id}>"
    prompt = re.sub(mention_pattern, "", prompt).strip()
    if not prompt:
        await message.reply("What would you like to talk about?", mention_author=False)
        return

    channel_id = message.channel.id
    try:
        async with message.channel.typing():
            response = await generate_response(channel_id, prompt)
        for chunk in chunk_message(response):
            await message.channel.send(chunk)
    except Exception:
        logger.exception("Failed to process a message in channel %s", channel_id)
        await message.channel.send(
            "Sorry, I couldn't process that message right now. Please try again later."
        )


def main():
    init_db()
    bot.run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()