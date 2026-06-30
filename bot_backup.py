import json
import os
import time
import traceback

from zoneinfo import ZoneInfo

import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import uuid

TOKEN = "8829999667:AAG719Vnp9bf9Mw99JDrZDQyweBXN-h_E2Y"
CHANNEL = "@thelostinwaves"
MUSIC_CHANNEL = "@acmmf"
ADMIN_IDS = [
    8305135192,
    8316171820
]

bot = telebot.TeleBot(TOKEN)
bot.delete_webhook()
scheduler = BackgroundScheduler(
    timezone=ZoneInfo("Asia/Tehran")
)

scheduler.start()
SCHED_FILE = "scheduled.json"
user_state = {}
pending_music = {}
draft = {}

def load_scheduled():
    if not os.path.exists(SCHED_FILE):
        return []

    try:
        with open(SCHED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_scheduled(data):
    try:
        with open(SCHED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Save Error: {e}")
        return False

def is_admin(uid):
    return uid in ADMIN_IDS

def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("📝 پست متنی", "🖼 پست با عکس")
    m.row("🎵 ارسال موزیک", "⏰ زمان‌بندی")
    m.row("📋 لیست زمان‌بندی", "🗑 حذف زمان‌بندی")
    m.row("📊 وضعیت")
    return m

@bot.message_handler(commands=["start"])
def start(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ دسترسی ندارید.")
        return
    bot.send_message(msg.chat.id, f"👋 سلام!\nکانال: {CHANNEL}\nموزیک: {MUSIC_CHANNEL}", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📝 پست متنی")
def text_post(msg):
    if not is_admin(msg.from_user.id): return
    user_state[msg.from_user.id] = "text"
    draft[msg.from_user.id] = {"type": "text"}
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add("❌ انصراف")
    bot.send_message(msg.chat.id, "📝 متن پست رو بنویس:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🖼 پست با عکس")
def photo_post(msg):
    if not is_admin(msg.from_user.id): return
    user_state[msg.from_user.id] = "photo"
    draft[msg.from_user.id] = {"type": "photo"}
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add("❌ انصراف")
    bot.send_message(msg.chat.id, "🖼 عکس رو بفرست:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🎵 ارسال موزیک")
def music_post(msg):
    if not is_admin(msg.from_user.id): return
    user_state[msg.from_user.id] = "music"
    draft[msg.from_user.id] = {"type": "music"}
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add("❌ انصراف")
    bot.send_message(msg.chat.id, "🎵 فایل موزیک رو بفرست:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "⏰ زمان‌بندی")
def sched_post(msg):
    if not is_admin(msg.from_user.id): return
    user_state[msg.from_user.id] = "sched_text"
    draft[msg.from_user.id] = {"type": "scheduled"}
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add("❌ انصراف")
    bot.send_message(msg.chat.id, "⏰ متن پست رو بنویس:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📋 لیست زمان‌بندی")
def list_sched(msg):
    if not is_admin(msg.from_user.id): return
    posts = load_scheduled()
    if not posts:
        bot.send_message(msg.chat.id, "📭 پست زمان‌بندی شده‌ای نداری.", reply_markup=main_menu())
        return
    text = "📋 پست‌های زمان‌بندی شده:\n\n"
    for i, p in enumerate(posts):
        text += f"{i+1}. ⏰ {p['time']}\n📝 {p['text'][:40]}\n\n"
    bot.send_message(msg.chat.id, text, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🗑 حذف زمان‌بندی")
def del_sched(msg):
    if not is_admin(msg.from_user.id): return
    posts = load_scheduled()
    if not posts:
        bot.send_message(msg.chat.id, "📭 پست زمان‌بندی شده‌ای نداری.", reply_markup=main_menu())
        return
    user_state[msg.from_user.id] = "delete_sched"
    text = "🗑 شماره پست رو بنویس:\n\n"
    for i, p in enumerate(posts):
        text += f"{i+1}. ⏰ {p['time']} - {p['text'][:30]}\n"
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add("❌ انصراف")
    bot.send_message(msg.chat.id, text, reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📊 وضعیت")
def status(msg):
    if not is_admin(msg.from_user.id): return
    count = len(load_scheduled())
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    bot.send_message(msg.chat.id, f"📊 وضعیت:\n✅ آنلاین\n📢 {CHANNEL}\n🎵 {MUSIC_CHANNEL}\n⏰ زمان‌بندی: {count} پست\n🕐 {now}", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "❌ انصراف")
def cancel(msg):
    uid = msg.from_user.id
    user_state.pop(uid, None)
    draft.pop(uid, None)
    bot.send_message(msg.chat.id, "❌ انصراف.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "text", content_types=["text"])
def recv_text(msg):
    uid = msg.from_user.id

    draft[uid]["text"] = msg.text

    user_state[uid] = "ask_music"

    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("✅ بله", "❌ خیر")

    bot.send_message(
        msg.chat.id,
        "🎵 آیا برای این پست موزیک هم می‌خوای اضافه کنی؟",
        reply_markup=mk
    )

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "ask_music" and m.text == "❌ خیر")
def no_music(msg):
    uid = msg.from_user.id

    user_state[uid] = "confirm"

    show_preview(msg, draft[uid])


@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "ask_music" and m.text == "✅ بله")
def yes_music(msg):
    uid = msg.from_user.id

    user_state[uid] = "music_name"

    bot.send_message(
        msg.chat.id,
        "🎵 اسم موزیک رو بنویس:"
    )

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "photo", content_types=["photo"])
def recv_photo(msg):
    uid = msg.from_user.id
    draft[uid]["photo_id"] = msg.photo[-1].file_id
    draft[uid]["caption"] = msg.caption or ""
    user_state[uid] = "confirm"
    show_preview(msg, draft[uid])

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "music", content_types=["audio", "document"])
def recv_music(msg):
    uid = msg.from_user.id
    if msg.audio:
        draft[uid]["audio_id"] = msg.audio.file_id
        draft[uid]["title"] = msg.audio.title or "موزیک"
    else:
        draft[uid]["audio_id"] = msg.document.file_id
        draft[uid]["title"] = msg.document.file_name or "موزیک"
    draft[uid]["caption"] = msg.caption or ""
    user_state[uid] = "confirm"
    show_preview(msg, draft[uid])

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "sched_text", content_types=["text"])
def recv_sched_text(msg):
    uid = msg.from_user.id
    draft[uid]["text"] = msg.text
    user_state[uid] = "sched_time"
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.add("❌ انصراف")
    bot.send_message(msg.chat.id, "⏰ زمان رو بنویس (مثلاً 14:30):", reply_markup=mk)

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "sched_time", content_types=["text"])
def recv_sched_time(msg):
    uid = msg.from_user.id
    try:
        datetime.strptime(msg.text.strip(), "%H:%M")
        draft[uid]["time"] = msg.text.strip()
        posts = load_scheduled()
        posts.append(draft[uid])
        save_scheduled(posts)
        add_schedule_job(draft[uid])
        user_state.pop(uid, None)
        draft.pop(uid, None)
        bot.send_message(msg.chat.id, f"✅ زمان‌بندی شد برای {msg.text.strip()}!", reply_markup=main_menu())
    except ValueError:
        bot.send_message(msg.chat.id, "❌ فرمت اشتباه! مثلاً: 14:30")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "delete_sched", content_types=["text"])
def recv_del_num(msg):

    uid = msg.from_user.id

    try:
        num = int(msg.text.strip()) - 1
        posts = load_scheduled()

        if 0 <= num < len(posts):
            removed = posts.pop(num)

            if removed.get("job_id"):
                try:
                    scheduler.remove_job(removed["job_id"])
                except:
                    pass

            save_scheduled(posts)

            user_state.pop(uid, None)

            bot.send_message(
                msg.chat.id,
                f"✅ پست {removed['time']} حذف شد.",
                reply_markup=main_menu()
            )
        else:
            bot.send_message(msg.chat.id, "❌ شماره معتبر نیست.")

    except ValueError:
        bot.send_message(msg.chat.id, "❌ عدد بنویس.")

def show_preview(msg, d):

    mk = types.InlineKeyboardMarkup()

    if d.get("buttons"):

        for b in d["buttons"]:

            if b["type"] == "music":

                mk.add(
                    types.InlineKeyboardButton(
                        text=b["text"],
                        url=b["url"]
                    )
                )

            elif b["type"] == "link":

                mk.add(
                    types.InlineKeyboardButton(
                        text=b["text"],
                        url=b["url"]
                    )
                )

            elif b["type"] == "popup":

                mk.add(
                    types.InlineKeyboardButton(
                        text=b["text"],
                        callback_data=b["id"]
                    )
                )

    mk.row(
        types.InlineKeyboardButton(
            "💬 پیام",
            callback_data="add_popup"
        ),
        types.InlineKeyboardButton(
            "🎵 موزیک",
            callback_data="add_music"
        )
    )

    mk.row(
        types.InlineKeyboardButton(
            "🔗 لینک",
            callback_data="add_link"
        )
    )

    mk.row(
        types.InlineKeyboardButton(
            "✅ ارسال",
            callback_data="send"
        ),
        types.InlineKeyboardButton(
            "❌ انصراف",
            callback_data="cancel"
        )
    )

    if d["type"] == "text":
        bot.send_message(
            msg.chat.id,
            "👁 پیش نمایش\n\n" + d["text"],
            reply_markup=mk
        )

    elif d["type"] == "photo":
        bot.send_photo(
            msg.chat.id,
            d["photo_id"],
            caption=d.get("caption", ""),
            reply_markup=mk
        )

    elif d["type"] == "music":
        bot.send_audio(
            msg.chat.id,
            d["audio_id"],
            caption=d.get("caption", ""),
            reply_markup=mk
        )
@bot.callback_query_handler(func=lambda c: c.data == "send")
def cb_send(call):
    uid = call.from_user.id
    d = draft.get(uid)

    if not d:
        bot.answer_callback_query(call.id, "❌ پستی پیدا نشد.")
        return

    try:
        mk = None

        if d.get("buttons"):
            mk = types.InlineKeyboardMarkup()

            for b in d["buttons"]:
                if b["type"] in ["music", "link"]:
                    mk.add(
                        types.InlineKeyboardButton(
                            text=b["text"],
                            url=b["url"]
                        )
                    )

                elif b["type"] == "popup":
                    mk.add(
                        types.InlineKeyboardButton(
                            text=b["text"],
                            callback_data=b["id"]
                        )
                    )

        if d["type"] == "text":
            bot.send_message(CHANNEL, d["text"], reply_markup=mk)

        elif d["type"] == "photo":
            bot.send_photo(
                CHANNEL,
                d["photo_id"],
                caption=d.get("caption", ""),
                reply_markup=mk
            )

        elif d["type"] == "music":
            bot.send_audio(
                MUSIC_CHANNEL,
                d["audio_id"],
                caption=d.get("caption", ""),
                reply_markup=mk
            )

        bot.edit_message_text(
            "✅ ارسال شد.",
            call.message.chat.id,
            call.message.message_id
        )

        user_state.pop(uid, None)
        draft.pop(uid, None)

        bot.send_message(
            call.message.chat.id,
            "🏠 منو",
            reply_markup=main_menu()
        )

    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ {e}")

def cb_cancel(call):
    uid = call.from_user.id
    user_state.pop(uid, None)
    draft.pop(uid, None)
    bot.edit_message_text("❌ لغو شد.", call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🏠 منو:", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data in ["add_popup", "add_music", "add_link"])
def cb_add_btn(call):
    uid = call.from_user.id

    draft.setdefault(uid, {})
    draft[uid]["btn_type"] = call.data.replace("add_", "")

    bot.send_message(
        call.message.chat.id,
        "نام دکمه را ارسال کن:"
    )

    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "btn_type" and m.text == "🎵 موزیک")
def btn_music(msg):
    uid = msg.from_user.id

    user_state[uid] = "btn_music_name"

    bot.send_message(
        msg.chat.id,
        "🎵 اسم موزیک را بنویس:"
    )
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "btn_music_name", content_types=["text"])
def recv_btn_music_name(msg):
    uid = msg.from_user.id

    if "buttons" not in draft[uid]:
        draft[uid]["buttons"] = []

    pending_music[uid] = {
        "text": msg.text
    }

    user_state[uid] = "btn_music_link"

    bot.send_message(
        msg.chat.id,
        "🔗 حالا لینک پست موزیک را ارسال کن:"
    )
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "btn_music_link", content_types=["text"])
def recv_btn_music_link(msg):
    uid = msg.from_user.id

    pending_music[uid]["url"] = msg.text

    draft[uid]["buttons"].append({
        "type": "music",
        "text": "🎵 " + pending_music[uid]["text"],
        "url": pending_music[uid]["url"]
    })

    pending_music.pop(uid)

    user_state[uid] = "confirm"

    bot.send_message(
        msg.chat.id,
        "✅ دکمه موزیک اضافه شد."
    )

    show_preview(msg, draft[uid])

    uid = call.from_user.id

    user_state[uid] = "btn_type"

    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)

    mk.row("🎵 موزیک", "📨 پیام")
    mk.row("🌐 لینک")
    mk.row("✅ پایان")

    bot.send_message(
        call.message.chat.id,
        "➕ نوع دکمه را انتخاب کن:",
        reply_markup=mk
    )

    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "add_btn", content_types=["text"])
def recv_btn(msg):
    uid = msg.from_user.id
    lines = msg.text.strip().split("\n")
    buttons = []
    for line in lines:
        if "|" in line:
            parts = line.split("|", 1)
            buttons.append({
    "type": "link",
    "text": parts[0].strip(),
    "url": parts[1].strip()
})
    if buttons:
        draft[uid]["buttons"] = buttons
        user_state[uid] = "confirm"
        bot.send_message(msg.chat.id, f"✅ {len(buttons)} دکمه اضافه شد!")
        show_preview(msg, draft[uid])
    else:
        bot.send_message(msg.chat.id, "❌ فرمت اشتباه!\nمثلاً: کانال ما | https://t.me/test")

def send_scheduled(post_text):
    print(f"ارسال زمان‌بندی: {post_text}")

    try:
        bot.send_message(CHANNEL, post_text)
        print("✅ پست زمان‌بندی ارسال شد")
    except Exception as e:
        print(f"❌ خطا: {e}")

def add_schedule_job(post):
    h, m = post["time"].split(":")

    job_id = post.get("job_id")

    if not job_id:
        job_id = str(uuid.uuid4())
        post["job_id"] = job_id

        posts = load_scheduled()
        for i in range(len(posts)):
            if posts[i]["time"] == post["time"] and posts[i]["text"] == post["text"]:
                posts[i]["job_id"] = job_id
                break
        save_scheduled(posts)

    scheduler.add_job(
        send_scheduled,
        "cron",
        id=job_id,
        hour=int(h),
        minute=int(m),
        args=[post["text"]],
        replace_existing=True
    )
print("درحال بارگذاری زمان‌بندی‌ها...")

for p in load_scheduled():
    add_schedule_job(p)

print("🤖 ربات آماده‌ست!")
print(f"📢 کانال: {CHANNEL}")
print(f"🎵 موزیک: {MUSIC_CHANNEL}")

while True:
    try:
        print("🤖 Bot Started")
        bot.infinity_polling(
            skip_pending=True,
            timeout=30,
            long_polling_timeout=30
        )

    except Exception as e:
        import traceback
        print(f"Polling Error: {e}")
        traceback.print_exc()
        time.sleep(5)
