import os
import asyncio
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # مهم لRailway

ALLOWED_USERS = {123456789, 987654321}  # حط IDs حقكم

chat_state = {}
MESSAGES = [
    "رسالة عشوائية 1",
    "رسالة عشوائية 2",
    "رسالة عشوائية 3",
]

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USERS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("بوت مزعج جاهز. استخدم /speed لاختيار السرعة و /stop لإيقافه.")

async def speed_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return

    keyboard = [
        [
            InlineKeyboardButton("سريع", callback_data="speed_fast"),
            InlineKeyboardButton("متوسط", callback_data="speed_medium"),
            InlineKeyboardButton("بطيء", callback_data="speed_slow"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر سرعة الإرسال:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_allowed(user_id):
        return

    chat_id = query.message.chat_id
    data = query.data

    if data == "speed_fast":
        speed = 2
    elif data == "speed_medium":
        speed = 5
    elif data == "speed_slow":
        speed = 10
    else:
        return

    chat_state[chat_id] = {"running": True, "speed": speed}
    await query.edit_message_text(f"بدأ الإرسال بسرعة: {speed} ثانية بين كل رسالة.")
    context.application.create_task(send_random_loop(chat_id, context))

async def send_random_loop(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    while chat_state.get(chat_id, {}).get("running", False):
        msg = random.choice(MESSAGES)
        await context.bot.send_message(chat_id=chat_id, text=msg)
        await asyncio.sleep(chat_state[chat_id]["speed"])

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return

    chat_id = update.effective_chat.id
    if chat_id in chat_state:
        chat_state[chat_id]["running"] = False
        await update.message.reply_text("تم إيقاف الإرسال.")

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("speed", speed_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
