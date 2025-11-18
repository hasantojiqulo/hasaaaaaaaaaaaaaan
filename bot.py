import os
import logging
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Railway + mahalliy .env ikkalasida ham ishlaydi
from dotenv import load_dotenv
load_dotenv()  # .env fayl boʻlsa oʻqiydi, yoʻq boʻlsa muammo emas

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Railway Variables ga qoʻshing yoki .env fayl yarating.")

# Majburiy kanallar
REQUIRED_CHANNELS = [
    "@mrxakimoff_eftbl",
    "@hasantojiqulovoffical"
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- DATABASE -------------------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS allowed_users
                 (user_id INTEGER PRIMARY KEY, added_at TEXT)""")
    conn.commit()
    conn.close()

def is_allowed(user_id: int) -> bool:
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM allowed_users WHERE user_id = ?", (user_id,))
    result = c.fetchone() is not None
    conn.close()
    return result

def add_allowed(user_id: int):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO allowed_users (user_id, added_at) VALUES (?, ?)",
              (user_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ------------------- OBUNA + KLAVYATURA -------------------
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
    keyboard = []
    for ch in REQUIRED_CHANNELS:
        keyboard.append([InlineKeyboardButton(f"Obuna bo'lish → {ch}", url=f"https://t.me/{ch[1:]}")])
    keyboard.append([InlineKeyboardButton("Tekshirish", callback_data="check")])
    return InlineKeyboardMarkup(keyboard)

# ------------------- SPAM ANIQLASH -------------------
def is_spam(msg):
    if not msg: return False
    text = (msg.text or "") + (msg.caption or "")
    if text and any(x in text.lower() for x in ["http", "t.me/", "@", "www.", ".com", ".uz", ".ru", "bit.ly"]):
        return True
    if msg.forward_origin: return True
    return bool(msg.photo or msg.video or msg.animation or msg.sticker or
                msg.document or msg.audio or msg.voice or msg.poll or
                msg.location or msg.contact)

# ------------------- HANDLERLAR -------------------
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if chat.type not in ("group", "supergroup"):
        return

    if is_allowed(user.id):
        return

    if is_spam(msg):
        try:
            await msg.delete()
        except:
            pass

        text = f"@{user.username or user.first_name or 'User'} reklama va media taqiqlangan!\n\nReklama qilish uchun quyidagi kanallarga obuna boʻling:"
        await chat.send_message(text, reply_markup=get_keyboard(), disable_web_page_preview=True)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "check":
        if await check_sub(context.bot, q.from_user.id):
            add_allowed(q.from_user.id)
            await q.edit_message_text("Muvaffaqiyatli! Endi reklama qilishingiz mumkin.")
        else:
            await q.edit_message_text("Hali barcha kanallarga obuna boʻlmagansiz!", reply_markup=get_keyboard())

# ------------------- ERROR HANDLER -------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Xato: {context.error}", exc_info=True)

# ------------------- MAIN -------------------
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(button))
    app.add_error_handler(error_handler)

    print("Bot Railway’da muvaffaqiyatli ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
