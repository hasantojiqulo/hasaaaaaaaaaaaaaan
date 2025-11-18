# bot.py — Bir marta ogohlantirish + keyin jim oʻchirish

import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Railway Variables ga qoʻshing.")

REQUIRED_CHANNELS = [
    "@mrxakimoff_eftbl",
    "@hasantojiqulovoffical"
]

CREATOR_TEXT = "Bot yaratuvchisi: Tojiqulov Hasan\n☎ +998-90-684-08-11"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- BAZA (faqat bitta ogohlantirish uchun) ----------
def init_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS warned_users
                 (user_id INTEGER PRIMARY KEY)""")
    c.execute("""CREATE TABLE IF NOT EXISTS allowed_users
                 (user_id INTEGER PRIMARY KEY)""")
    conn.commit()
    conn.close()

def was_warned(user_id: int) -> bool:
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT 1 FROM warned_users WHERE user_id = ?", (user_id,))
    res = c.fetchone() is not None
    conn.close()
    return res

def mark_warned(user_id: int):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO warned_users VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def is_allowed(user_id: int) -> bool:
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT 1 FROM allowed_users WHERE user_id = ?", (user_id,))
    res = c.fetchone() is not None
    conn.close()
    return res

def add_allowed(user_id: int):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO allowed_users VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# ---------- OBUNA TEKSHIRISH ----------
async def check_sub(bot, user_id: int) -> bool:
    for ch in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ("left", "kicked", "banned"):
                return False
        except:
            return False
    return True

def get_keyboard():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([InlineKeyboardButton(f"Obuna boʻlish → {ch}", url=f"https://t.me/{ch[1:]}")])
    kb.append([InlineKeyboardButton("Obuna boʻldim", callback_data="check")])
    kb.append([InlineKeyboardButton("Bot yaratuvchisi", url="https://t.me/hasantojiqulovoffical")])
    return InlineKeyboardMarkup(kb)

# ---------- SPAM TEKSHIRISH ----------
def is_spam(msg):
    if not msg: return False
    text = (msg.text or "") + (msg.caption or "")
    if text and any(x in text.lower() for x in ["http", "t.me/", "@", "www.", ".com", ".uz", ".ru", "bit.ly", "t.co"]):
        return True
    if msg.forward_origin: return True
    return bool(msg.photo or msg.video or msg.animation or msg.sticker or
                msg.document or msg.audio or msg.voice or msg.poll or
                msg.location or msg.contact or msg.new_chat_members)

# ---------- ASOSIY LOGIKA ----------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        return

    if is_spam(msg):
        # Agar allaqachon ruxsat berilgan boʻlsa — oʻtkazamiz
        if is_allowed(user.id):
            return

        # Agar obuna boʻlgan boʻlsa — ruxsat beramiz
        if await check_sub(context.bot, user.id):
            add_allowed(user.id)
            return  # xabar qoladi

        # Obuna boʻlmagan boʻlsa
        try:
            await msg.delete()
        except:
            pass

        # Bir marta ogohlantirish
        if not was_warned(user.id):
            mark_warned(user.id)
            text = (
                f"@{user.username or user.first_name or 'Foydalanuvchi'}\n\n"
                f"Reklama va media guruhda taqiqlangan!\n"
                f"Faqat quyidagi kanallarga obuna boʻlganlar reklama qilishi mumkin:"
            )
            await chat.send_message(text, reply_markup=get_keyboard(), disable_web_page_preview=True)
        # Keyingi safarlar — jimgina oʻchirish, hech narsa yozmaslik

# ---------- TUGMA ----------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "check":
        if await check_sub(context.bot, q.from_user.id):
            add_allowed(q.from_user.id)
            await q.edit_message_text(
                "Tabriklaymiz! Endi reklama qilishingiz mumkin!\n\n"
                f"{CREATOR_TEXT}"
            )
        else:
            await q.edit_message_text(
                "Hali obuna boʻlmagansiz! Obuna boʻlib qayta bosing.",
                reply_markup=get_keyboard()
            )

# ---------- MAIN ----------
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle))
    app.add_handler(CallbackQueryHandler(button))

    print("Bot faollashtirildi → Bir marta ogohlantirish + keyin jim blok!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
