import asyncio
import json
import os
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_KEY = os.environ["LLM_API_KEY"]
BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
MODEL_ID = os.environ["MODEL_ID"]
DB = "chatbot.db"

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
bot = Bot(TOKEN)
dp = Dispatcher()

with open("character.json", encoding="utf-8") as f:
    DEFAULT_CHARACTER = json.load(f)

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, adult_confirmed INTEGER DEFAULT 0, scenario TEXT);
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT, content TEXT);
        """)
        await db.commit()

async def ensure_user(uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
        await db.commit()

async def is_adult(uid):
    await ensure_user(uid)
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT adult_confirmed FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        return bool(row and row[0])

async def get_scenario(uid):
    await ensure_user(uid)
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT scenario FROM users WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        return (row and row[0]) or DEFAULT_CHARACTER["scenario"]

async def get_history(uid, limit=30):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit))
        rows = await cur.fetchall()
    return [{"role": r, "content": c} for r, c in reversed(rows)]

async def add_message(uid, role, content):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO messages(user_id, role, content) VALUES(?,?,?)", (uid, role, content))
        await db.commit()

async def clear_history(uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM messages WHERE user_id=?", (uid,))
        await db.commit()

def system_prompt(scenario):
    c = DEFAULT_CHARACTER
    return f"""You are roleplaying as a fictional character.
Name: {c['name']}
Age: {c['age']}
Personality: {c['personality']}
Speaking style: {c['speaking_style']}
Relationship: {c['relationship']}
Scenario: {scenario}

Stay in character and preserve continuity. Use natural dialogue, actions, emotions and scene details when appropriate.
All characters participating in sexual content must be explicitly 18 or older. Never sexualize minors. Do not depict sexual activity involving anyone unwilling or unable to consent. Treat this as fictional roleplay."""

async def generate(uid):
    scenario = await get_scenario(uid)
    messages = [{"role": "system", "content": system_prompt(scenario)}] + await get_history(uid)
    res = await client.chat.completions.create(model=MODEL_ID, messages=messages, temperature=0.95, max_tokens=900)
    return res.choices[0].message.content or "..."

@dp.message(Command("start"))
async def start(message: Message):
    await ensure_user(message.from_user.id)
    await message.answer("Welcome. This bot is for adults (18+) only. If you are 18 or older, send /iam18 to continue.\n\nCommands after confirmation: /scenario, /character, /reset")

@dp.message(Command("iam18"))
async def adult(message: Message):
    uid = message.from_user.id
    await ensure_user(uid)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET adult_confirmed=1 WHERE user_id=?", (uid,))
        await db.commit()
    await message.answer("18+ confirmation saved. Send a message to begin roleplay, or use /scenario <description>.")

@dp.message(Command("reset"))
async def reset(message: Message):
    await clear_history(message.from_user.id)
    await message.answer("Conversation reset.")

@dp.message(Command("character"))
async def character(message: Message):
    c = DEFAULT_CHARACTER
    await message.answer(f"Name: {c['name']}\nAge: {c['age']}\nPersonality: {c['personality']}\nStyle: {c['speaking_style']}")

@dp.message(Command("scenario"))
async def scenario(message: Message):
    uid = message.from_user.id
    if not await is_adult(uid):
        await message.answer("Use /iam18 first.")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 1:
        await message.answer("Current scenario:\n" + await get_scenario(uid))
        return
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET scenario=? WHERE user_id=?", (parts[1].strip(), uid))
        await db.commit()
    await clear_history(uid)
    await message.answer("Scenario updated. Send your opening message.")

@dp.message(F.text)
async def chat(message: Message):
    uid = message.from_user.id
    if not await is_adult(uid):
        await message.answer("This bot is 18+ only. If you are 18 or older, send /iam18 first.")
        return
    await add_message(uid, "user", message.text)
    try:
        await bot.send_chat_action(message.chat.id, "typing")
        reply = await generate(uid)
        await add_message(uid, "assistant", reply)
        await message.answer(reply)
    except Exception as exc:
        print(repr(exc))
        await message.answer("Model request failed. Check LLM_API_KEY, LLM_BASE_URL and MODEL_ID.")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
