import os
import logging
import random
from typing import Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    Job,
)

# ---------------- إعدادات عامة ---------------- #

# تفعيل اللوق للمساعدة في تتبع أي مشكلة
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# التوكن من متغير البيئة (مهم لـ Railway أو أي استضافة سحابية)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

# ضع هنا أرقام الـ user_id المسموح لهم بالتحكم في البوت
ALLOWED_USERS = {
    824219206,  # استبدلها بـ user_id حقك
    735911806,  # واستبدلها بـ user_id حق الشخص الثاني
}

# سرعات الإرسال بالثواني
SPEEDS = {
    "speed_fast": 2,    # سريع
    "speed_medium": 5,  # متوسط
    "speed_slow": 10,   # بطيء
}

# حالة القروبات: نخزن الوظيفة (Job) الحالية لكل قروب إن وجدت
chat_jobs: Dict[int, Job] = {}

# قائمة الرسائل العشوائية - عدّلها كما تحب
MESSAGES = [
    "رسالة عشوائية 1",
    "رسالة عشوائية 2",
    "رسالة عشوائية 3",
    "رسالة عشوائية 4",
]


# ---------------- دوال مساعدة ---------------- #

def is_allowed_user(user_id: int) -> bool:
    """يتأكد أن المستخدم من ضمن الحسابين المصرح لهم."""
    return user_id in ALLOWED_USERS


def cancel_chat_job(chat_id: int) -> None:
    """يلغي أي Job مرتبط بهذا القروب إن وجد."""
    job = chat_jobs.get(chat_id)
    if job:
        job.schedule_removal()
        chat_jobs.pop(chat_id, None)


# ---------------- أوامر البوت ---------------- #

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /start للترحيب وتوضيح الأوامر."""
    await update.message.reply_text(
        "بوت مزعج جاهز.\n"
        "الأوامر المتاحة:\n"
        "/speed لاختيار سرعة الإرسال\n"
        "/stop لإيقاف الإرسال"
    )


async def speed_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /speed لعرض خيارات السرعة."""
    user = update.effective_user
    if not user or not is_allowed_user(user.id):
        return  # تجاهل أي مستخدم غير مسموح

    keyboard = [
        [
            InlineKeyboardButton("🚀 سريع", callback_data="speed_fast"),
            InlineKeyboardButton("⏱ متوسط", callback_data="speed_medium"),
            InlineKeyboardButton("🐢 بطيء", callback_data="speed_slow"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "اختر سرعة الإرسال التي تريد أن يبدأ بها البوت:",
        reply_markup=reply_markup,
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر /stop لإيقاف الإرسال في هذا القروب."""
    user = update.effective_user
    chat = update.effective_chat

    if not user or not is_allowed_user(user.id):
        return

    if not chat:
        return

    chat_id = chat.id
    if chat_id in chat_jobs:
        cancel_chat_job(chat_id)
        await update.message.reply_text("تم إيقاف الإرسال في هذا القروب.")
    else:
        await update.message.reply_text("ما في إرسال شغال حاليًا في هذا القروب.")


# ---------------- التعامل مع الأزرار ---------------- #

async def speed_button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """معالجة ضغط زر السرعة من الـ Inline Keyboard."""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    message = query.message

    if not user or not is_allowed_user(user.id):
        return

    if not message:
        return

    chat_id = message.chat_id
    data = query.data  # مثل: "speed_fast"

    if data not in SPEEDS:
        return

    # نحدّد السرعة بناء على الزر
    interval_seconds = SPEEDS[data]

    # نلغي أي Job قديم لهذا القروب
    cancel_chat_job(chat_id)

    # ننشئ Job جديد للإرسال المتكرر
    job: Job = context.job_queue.run_repeating(
        send_random_message_job,
        interval=interval_seconds,
        first=0.0,  # يبدأ فورًا
        chat_id=chat_id,
        name=f"spam_{chat_id}",
        data={"interval": interval_seconds},
    )
    chat_jobs[chat_id] = job

    # نحدّث رسالة الاختيار
    text_speed = {
        "speed_fast": "سريع (كل 2 ثانية تقريبًا)",
        "speed_medium": "متوسط (كل 5 ثواني تقريبًا)",
        "speed_slow": "بطيء (كل 10 ثواني تقريبًا)",
    }.get(data, f"كل {interval_seconds} ثانية")

    await query.edit_message_text(
        f"تم تشغيل الإرسال العشوائي في هذا القروب.\n"
        f"السرعة الحالية: {text_speed}\n"
        f"لإيقاف الإرسال استخدم الأمر: /stop"
    )


# ---------------- Job الإرسال العشوائي ---------------- #

async def send_random_message_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """دالة الـ Job التي ترسل رسالة عشوائية في كل تكرار."""
    job = context.job
    if not job:
        return

    chat_id = job.chat_id

    # اختيار رسالة عشوائية
    msg = random.choice(MESSAGES)

    try:
        await context.bot.send_message(chat_id=chat_id, text=msg)
    except Exception as e:
        logger.error(f"Error sending message to chat {chat_id}: {e}")
        # لو صار خطأ كثير ممكن نلغي الجوب لتجنب مشاكل
        # cancel_chat_job(chat_id)


# ---------------- نقطة الدخول الرئيسية ---------------- #

def main() -> None:
    """تجهيز وتشغيل البوت باستخدام Long Polling."""
    application = Application.builder().token(BOT_TOKEN).build()

    # أوامر
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("speed", speed_command))
    application.add_handler(CommandHandler("stop", stop_command))

    # أزرار السرعة
    application.add_handler(CallbackQueryHandler(speed_button_handler))

    # تشغيل البوت
    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    main()
