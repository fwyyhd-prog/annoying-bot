import os
import asyncio
import random
import logging

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============ الإعدادات ============

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# حط أرقام حسابك وحساب الشخص الثاني فقط
ALLOWED_USERS = {
    824219206,
    735911806,
}

# لا تجعل "سريع" أقل من ثانيتين حتى لا يسبب مشاكل إرسال
SPEEDS = {
    "🚀 سريع": 2,
    "⏱️ متوسط": 5,
    "🐢 بطيء": 10,
}

MESSAGES = [
    "رسالة عشوائية 1",
    "رسالة عشوائية 2",
    "رسالة عشوائية 3",
    "رسالة عشوائية 4",
]

# نخزن Task واحد لكل قروب
running_tasks = {}

MENU = ReplyKeyboardMarkup(
    [
        ["🚀 سريع", "⏱️ متوسط", "🐢 بطيء"],
        ["⛔ إيقاف", "ℹ️ الحالة"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


# ============ دوال مساعدة ============

def allowed(update: Update) -> bool:
    """يتأكد أن المتحكم هو أحد الحسابين المسموحين."""
    user = update.effective_user
    return bool(user and user.id in ALLOWED_USERS)


def stop_sender(chat_id: int) -> bool:
    """يلغي الإرسال الحالي للقروب ويعيد True لو كان شغال."""
    task = running_tasks.pop(chat_id, None)

    if task and not task.done():
        task.cancel()
        return True

    return False


async def send_loop(chat_id: int, context: ContextTypes.DEFAULT_TYPE, seconds: int):
    """إرسال متكرر إلى أن يتم الإيقاف."""
    try:
        while True:
            await context.bot.send_message(
                chat_id=chat_id,
                text=random.choice(MESSAGES),
            )
            await asyncio.sleep(seconds)

    except asyncio.CancelledError:
        # يحدث بشكل طبيعي عند ضغط زر إيقاف أو تغيير سرعة
        raise

    except Exception as error:
        logging.exception("خطأ أثناء الإرسال للقروب %s: %s", chat_id, error)


# ============ الأوامر والأزرار ============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض لوحة الأزرار."""
    if not allowed(update):
        return

    await update.message.reply_text(
        "جاهز ✅\n"
        "اختر السرعة لبدء الإرسال، أو اضغط ⛔ إيقاف.",
        reply_markup=MENU,
    )


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يتعامل مع أزرار لوحة التحكم."""
    if not allowed(update):
        return

    chat = update.effective_chat
    message = update.effective_message

    if not chat or not message:
        return

    chat_id = chat.id
    choice = message.text

    # إيقاف
    if choice == "⛔ إيقاف":
        if stop_sender(chat_id):
            await message.reply_text("تم إيقاف الإرسال ⛔", reply_markup=MENU)
        else:
            await message.reply_text("ما فيه إرسال شغّال الآن.", reply_markup=MENU)
        return

    # حالة
    if choice == "ℹ️ الحالة":
        task = running_tasks.get(chat_id)
        if task and not task.done():
            await message.reply_text("الإرسال شغّال الآن ✅", reply_markup=MENU)
        else:
            await message.reply_text("الإرسال متوقف حاليًا ⛔", reply_markup=MENU)
        return

    # اختيار سرعة
    if choice in SPEEDS:
        seconds = SPEEDS[choice]

        # يوقف أي إرسال سابق قبل تشغيل سرعة جديدة
        stop_sender(chat_id)

        # ينشئ مهمة واحدة فقط للقروب
        task = asyncio.create_task(send_loop(chat_id, context, seconds))
        running_tasks[chat_id] = task

        await message.reply_text(
            f"تم التشغيل: {choice}\n"
            f"رسالة كل {seconds} ثوانٍ.\n"
            f"للإيقاف اضغط ⛔ إيقاف.",
            reply_markup=MENU,
        )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """في حال أرسل أمرًا غير معروف، يعيد إظهار القائمة."""
    if allowed(update):
        await update.message.reply_text(
            "استخدم الأزرار الموجودة أسفل المحادثة.",
            reply_markup=MENU,
        )


# ============ تشغيل البوت ============

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
