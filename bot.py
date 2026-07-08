import telebot
import json
import os
import time
import uuid
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = "8829999667:AAFBCa3fNPE8yB-MhzUxaCoSEg4X5AG17Fs"
OWNER_IDS = [8305135192, 8316171820]
IRAN_TZ = ZoneInfo("Asia/Tehran")

bot = telebot.TeleBot(TOKEN)
bot.delete_webhook()
scheduler = BackgroundScheduler(timezone=IRAN_TZ)
scheduler.start()

SCHED_FILE = "scheduled.json"
CHANNELS_FILE = "channels.json"
ADMINS_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
user_state = {}
draft = {}

# ===================== فایل‌های ذخیره‌سازی =====================
def load_settings():
    default = {"music_channel": "@theLOSTinSOUNDS"}
    if not os.path.exists(SETTINGS_FILE):
        save_settings(default)
        return default
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save Settings Error: {e}")

def get_music_channel():
    return load_settings().get("music_channel", "@theLOSTinSOUNDS")

def load_admins():
    if not os.path.exists(ADMINS_FILE):
        save_admins(OWNER_IDS[:])
        return OWNER_IDS[:]
    try:
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return OWNER_IDS[:]

def save_admins(data):
    try:
        with open(ADMINS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save Admins Error: {e}")

def load_channels():
    if not os.path.exists(CHANNELS_FILE):
        default = [{"name": "کانال اصلی", "username": "@thelostinwaves"}]
        save_channels(default)
        return default
    try:
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_channels(data):
    try:
        with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save Channels Error: {e}")

def load_scheduled():
    if not os.path.exists(SCHED_FILE):
        return []
    try:
        with open(SCHED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_scheduled(data):
    try:
        with open(SCHED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save Error: {e}")

# ===================== توابع کمکی =====================
def is_admin(uid):
    return uid in load_admins()

def is_owner(uid):
    return uid in OWNER_IDS

def now_iran():
    return datetime.now(IRAN_TZ).strftime("%Y-%m-%d %H:%M")

def main_menu(uid=None):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("📝 پست متنی", "🖼 پست با عکس")
    m.row("🎬 پست با ویدیو", "🎵 ارسال موزیک")
    m.row("⏰ زمان‌بندی‌ها", "📺 مدیریت کانال‌ها")
    m.row("⚙️ تنظیمات", "📊 وضعیت")
    if uid and is_owner(uid):
        m.row("👥 مدیریت ادمین‌ها")
    return m

def channel_select_menu():
    channels = load_channels()
    mk = types.InlineKeyboardMarkup()
    for ch in channels:
        mk.add(types.InlineKeyboardButton(
            f"📢 {ch['name']} ({ch['username']})",
            callback_data=f"selch:{ch['username']}"
        ))
    return mk

def back_cancel_kb():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("⬅️ برگشت", "❌ انصراف")
    return mk

def ask_schedule_kb():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("⏰ زمان‌بندی کن", "✅ همین الان ارسال کن")
    mk.row("❌ انصراف")
    return mk

# ===================== شروع =====================
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    if not is_admin(uid):
        bot.reply_to(msg, "❌ دسترسی ندارید.")
        return
    channels = load_channels()
    ch_list = "\n".join([f"• {c['name']}: {c['username']}" for c in channels])
    bot.send_message(
        msg.chat.id,
        f"👋 سلام!\n\n📺 کانال‌ها:\n{ch_list}\n\n🎵 موزیک: {get_music_channel()}\n🕐 زمان ایران: {now_iran()}",
        reply_markup=main_menu(uid)
    )

@bot.message_handler(func=lambda m: m.text == "❌ انصراف")
def cancel(msg):
    uid = msg.from_user.id
    user_state.pop(uid, None)
    draft.pop(uid, None)
    bot.send_message(msg.chat.id, "❌ انصراف.", reply_markup=main_menu(uid))

# ===================== برگشت یک مرحله =====================
PREV_STATE = {
    "text":            ("select_channel", None),
    "photo":           ("select_channel", None),
    "video":           ("select_channel", None),
    "music":           (None, None),
    "ask_music":       ("text", "📝 متن پست رو دوباره بنویس:"),
    "music_for_text":  ("ask_music", None),
    "sched_text":      ("select_channel", None),
    "sched_datetime":  ("sched_text", "📝 متن پست رو دوباره بنویس:"),
    "popup_text":      ("confirm", None),
    "popup_btn_name":  ("popup_text", "💬 متن پاپ‌آپ رو دوباره بنویس:"),
    "link_text":       ("confirm", None),
    "link_url":        ("link_text", "🔗 اسم دکمه لینک رو دوباره بنویس:"),
    "add_ch_name":     (None, None),
    "add_ch_username": ("add_ch_name", "📝 اسم کانال رو دوباره بنویس:"),
    "add_admin_id":    (None, None),
}

@bot.message_handler(func=lambda m: m.text == "⬅️ برگشت")
def go_back(msg):
    uid = msg.from_user.id
    current = user_state.get(uid)

    if not current:
        bot.send_message(msg.chat.id, "🏠 منو:", reply_markup=main_menu(uid))
        return

    prev_info = PREV_STATE.get(current)
    if not prev_info:
        user_state.pop(uid, None)
        draft.pop(uid, None)
        bot.send_message(msg.chat.id, "🏠 منو:", reply_markup=main_menu(uid))
        return

    prev_state, prompt = prev_info

    if prev_state == "select_channel":
        user_state[uid] = f"select_channel_{draft.get(uid, {}).get('type', 'text')}"
        bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())
        return

    if prev_state == "ask_music":
        user_state[uid] = "ask_music"
        mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
        mk.row("✅ بله", "❌ خیر")
        mk.row("⬅️ برگشت", "❌ انصراف")
        bot.send_message(msg.chat.id, "🎵 موزیک هم اضافه کنی؟", reply_markup=mk)
        return

    if prev_state == "confirm":
        user_state[uid] = "confirm"
        show_preview(msg, draft.get(uid, {}))
        return

    if prev_state is None:
        user_state.pop(uid, None)
        draft.pop(uid, None)
        bot.send_message(msg.chat.id, "🏠 منو:", reply_markup=main_menu(uid))
        return

    user_state[uid] = prev_state
    bot.send_message(msg.chat.id, prompt or "ادامه بده:", reply_markup=back_cancel_kb())

# ===================== تنظیمات =====================
@bot.message_handler(func=lambda m: m.text == "⚙️ تنظیمات")
def settings_menu(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    settings = load_settings()
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton(
        f"🎵 کانال موزیک: {settings['music_channel']}",
        callback_data="change_music_ch"
    ))
    bot.send_message(msg.chat.id, "⚙️ تنظیمات:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "change_music_ch")
def cb_change_music_ch(call):
    uid = call.from_user.id
    if not is_admin(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید")
        return
    user_state[uid] = "change_music_ch"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"🎵 کانال موزیک فعلی: {get_music_channel()}\n\nیوزرنیم جدید رو بنویس (مثلاً @channel):",
        reply_markup=back_cancel_kb()
    )

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "change_music_ch", content_types=["text"])
def recv_new_music_ch(msg):
    uid = msg.from_user.id
    username = msg.text.strip()
    if not username.startswith("@"):
        username = "@" + username
    settings = load_settings()
    old = settings["music_channel"]
    settings["music_channel"] = username
    save_settings(settings)
    user_state.pop(uid, None)
    bot.send_message(
        msg.chat.id,
        f"✅ کانال موزیک از {old} به {username} تغییر کرد!",
        reply_markup=main_menu(uid)
    )

# ===================== مدیریت کانال‌ها =====================
@bot.message_handler(func=lambda m: m.text == "📺 مدیریت کانال‌ها")
def manage_channels(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    channels = load_channels()
    text = "📺 کانال‌های فعلی:\n\n"
    for i, c in enumerate(channels):
        text += f"{i+1}. {c['name']} - {c['username']}\n"
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("➕ افزودن کانال", callback_data="add_channel"))
    if channels:
        mk.add(types.InlineKeyboardButton("🗑 حذف کانال", callback_data="remove_channel_menu"))
    bot.send_message(msg.chat.id, text, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "add_channel")
def cb_add_channel(call):
    uid = call.from_user.id
    user_state[uid] = "add_ch_name"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📝 اسم کانال رو بنویس:", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "add_ch_name", content_types=["text"])
def recv_ch_name(msg):
    uid = msg.from_user.id
    draft[uid] = {"ch_name": msg.text}
    user_state[uid] = "add_ch_username"
    bot.send_message(msg.chat.id, "🔗 یوزرنیم کانال رو بنویس (@channel):", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "add_ch_username", content_types=["text"])
def recv_ch_username(msg):
    uid = msg.from_user.id
    username = msg.text.strip()
    if not username.startswith("@"):
        username = "@" + username
    channels = load_channels()
    channels.append({"name": draft[uid]["ch_name"], "username": username})
    save_channels(channels)
    user_state.pop(uid, None)
    draft.pop(uid, None)
    bot.send_message(msg.chat.id, f"✅ کانال «{username}» اضافه شد!", reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda c: c.data == "remove_channel_menu")
def cb_remove_channel_menu(call):
    channels = load_channels()
    mk = types.InlineKeyboardMarkup()
    for i, c in enumerate(channels):
        mk.add(types.InlineKeyboardButton(f"🗑 {c['name']}", callback_data=f"rmch:{i}"))
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "کدوم کانال حذف بشه؟", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rmch:"))
def cb_rm_channel(call):
    uid = call.from_user.id
    idx = int(call.data.replace("rmch:", ""))
    channels = load_channels()
    if 0 <= idx < len(channels):
        removed = channels.pop(idx)
        save_channels(channels)
        bot.answer_callback_query(call.id, f"✅ {removed['name']} حذف شد")
        bot.send_message(call.message.chat.id, f"✅ کانال «{removed['name']}» حذف شد.", reply_markup=main_menu(uid))
    else:
        bot.answer_callback_query(call.id, "❌ خطا")

# ===================== مدیریت ادمین‌ها =====================
@bot.message_handler(func=lambda m: m.text == "👥 مدیریت ادمین‌ها")
def manage_admins(msg):
    uid = msg.from_user.id
    if not is_owner(uid):
        bot.send_message(msg.chat.id, "❌ فقط ادمین‌های اصلی دسترسی دارن.", reply_markup=main_menu(uid))
        return
    admins = load_admins()
    text = "👥 ادمین‌های فعلی:\n\n"
    for a in admins:
        tag = " 👑" if a in OWNER_IDS else ""
        text += f"• {a}{tag}\n"
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("➕ افزودن ادمین", callback_data="add_admin"))
    removable = [a for a in admins if a not in OWNER_IDS]
    if removable:
        mk.add(types.InlineKeyboardButton("🗑 حذف ادمین", callback_data="remove_admin_menu"))
    bot.send_message(msg.chat.id, text, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "add_admin")
def cb_add_admin(call):
    uid = call.from_user.id
    if not is_owner(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید")
        return
    user_state[uid] = "add_admin_id"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🆔 آیدی عددی کاربر جدید رو بنویس:", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "add_admin_id", content_types=["text"])
def recv_admin_id(msg):
    uid = msg.from_user.id
    if not is_owner(uid): return
    try:
        new_id = int(msg.text.strip())
        admins = load_admins()
        if new_id in admins:
            bot.send_message(msg.chat.id, "⚠️ این کاربر از قبل ادمینه.", reply_markup=main_menu(uid))
            user_state.pop(uid, None)
            return
        admins.append(new_id)
        save_admins(admins)
        user_state.pop(uid, None)
        # بپرس ادمین کانال‌ها هم بشه؟
        draft[uid] = {"new_admin_id": new_id}
        user_state[uid] = "ask_channel_admin"
        channels = load_channels()
        if channels:
            mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
            mk.row("✅ بله", "❌ خیر")
            bot.send_message(
                msg.chat.id,
                f"✅ کاربر {new_id} به عنوان ادمین ربات اضافه شد!\n\nمی‌خوای این شخص رو در کانال‌ها هم ادمین کنم؟",
                reply_markup=mk
            )
        else:
            draft.pop(uid, None)
            bot.send_message(msg.chat.id, f"✅ کاربر {new_id} اضافه شد!", reply_markup=main_menu(uid))
    except ValueError:
        bot.send_message(msg.chat.id, "❌ آیدی باید عدد باشه:", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "ask_channel_admin", content_types=["text"])
def recv_channel_admin_answer(msg):
    uid = msg.from_user.id
    new_id = draft.get(uid, {}).get("new_admin_id")
    user_state.pop(uid, None)
    draft.pop(uid, None)
    if msg.text == "✅ بله" and new_id:
        channels = load_channels()
        results = []
        for ch in channels:
            try:
                bot.promote_chat_member(
                    ch["username"], new_id,
                    can_post_messages=True,
                    can_edit_messages=True,
                    can_delete_messages=True
                )
                results.append(f"✅ {ch['name']}")
            except Exception as e:
                results.append(f"❌ {ch['name']}: {e}")
        bot.send_message(
            msg.chat.id,
            "نتیجه ادمین کردن در کانال‌ها:\n" + "\n".join(results),
            reply_markup=main_menu(uid)
        )
    else:
        bot.send_message(msg.chat.id, "✅ ادمین اضافه شد (فقط در ربات).", reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda c: c.data == "remove_admin_menu")
def cb_remove_admin_menu(call):
    uid = call.from_user.id
    if not is_owner(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید")
        return
    admins = load_admins()
    mk = types.InlineKeyboardMarkup()
    for a in admins:
        if a not in OWNER_IDS:
            mk.add(types.InlineKeyboardButton(f"🗑 {a}", callback_data=f"rmadmin:{a}"))
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "کدوم ادمین حذف بشه؟", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rmadmin:"))
def cb_rm_admin(call):
    uid = call.from_user.id
    if not is_owner(uid):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید")
        return
    target_id = int(call.data.replace("rmadmin:", ""))
    if target_id in OWNER_IDS:
        bot.answer_callback_query(call.id, "❌ ادمین اصلی قابل حذف نیست!")
        return
    admins = load_admins()
    if target_id in admins:
        admins.remove(target_id)
        save_admins(admins)
        bot.answer_callback_query(call.id, "✅ حذف شد")
        bot.send_message(call.message.chat.id, f"✅ ادمین {target_id} حذف شد.", reply_markup=main_menu(uid))

# ===================== انتخاب کانال =====================
@bot.message_handler(func=lambda m: m.text == "📝 پست متنی")
def text_post(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    user_state[uid] = "select_channel_text"
    draft[uid] = {"type": "text"}
    bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())

@bot.message_handler(func=lambda m: m.text == "🖼 پست با عکس")
def photo_post(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    user_state[uid] = "select_channel_photo"
    draft[uid] = {"type": "photo"}
    bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())

@bot.message_handler(func=lambda m: m.text == "🎬 پست با ویدیو")
def video_post(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    user_state[uid] = "select_channel_video"
    draft[uid] = {"type": "video"}
    bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())

@bot.message_handler(func=lambda m: m.text == "🎵 ارسال موزیک")
def music_post(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    user_state[uid] = "music"
    draft[uid] = {"type": "music"}
    bot.send_message(msg.chat.id, "🎵 فایل موزیک رو بفرست:", reply_markup=back_cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("selch:"))
def cb_select_channel(call):
    uid = call.from_user.id
    channel = call.data.replace("selch:", "")
    if uid not in draft:
        draft[uid] = {}
    draft[uid]["channel"] = channel
    bot.answer_callback_query(call.id)
    state = user_state.get(uid, "")
    mk = back_cancel_kb()
    if "text" in state:
        user_state[uid] = "text"
        bot.send_message(call.message.chat.id, "📝 متن پست رو بنویس:", reply_markup=mk)
    elif "photo" in state:
        user_state[uid] = "photo"
        bot.send_message(call.message.chat.id, "🖼 عکس رو بفرست:", reply_markup=mk)
    elif "video" in state:
        user_state[uid] = "video"
        bot.send_message(call.message.chat.id, "🎬 ویدیو رو بفرست:", reply_markup=mk)
    elif "sched" in state:
        user_state[uid] = "sched_text"
        bot.send_message(call.message.chat.id, "📝 متن پست رو بنویس:", reply_markup=mk)

# ===================== دریافت محتوا =====================
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "text", content_types=["text"])
def recv_text(msg):
    uid = msg.from_user.id
    draft[uid]["text"] = msg.text
    user_state[uid] = "ask_music"
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("✅ بله", "❌ خیر")
    mk.row("⬅️ برگشت", "❌ انصراف")
    bot.send_message(msg.chat.id, "🎵 موزیک هم اضافه کنی؟", reply_markup=mk)

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "ask_music" and m.text == "❌ خیر")
def no_music(msg):
    uid = msg.from_user.id
    user_state[uid] = "confirm"
    show_preview(msg, draft[uid])

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "ask_music" and m.text == "✅ بله")
def yes_music(msg):
    uid = msg.from_user.id
    user_state[uid] = "music_for_text"
    bot.send_message(msg.chat.id, "🎵 فایل موزیک رو بفرست:", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "music_for_text", content_types=["audio", "document"])
def recv_music_for_text(msg):
    uid = msg.from_user.id
    if msg.audio:
        draft[uid]["audio_id"] = msg.audio.file_id
        draft[uid]["music_title"] = msg.audio.title or "موزیک"
    else:
        draft[uid]["audio_id"] = msg.document.file_id
        draft[uid]["music_title"] = msg.document.file_name or "موزیک"
    user_state[uid] = "confirm"
    show_preview(msg, draft[uid])

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "photo", content_types=["photo"])
def recv_photo(msg):
    uid = msg.from_user.id
    draft[uid]["photo_id"] = msg.photo[-1].file_id
    draft[uid]["caption"] = msg.caption or ""
    user_state[uid] = "confirm"
    show_preview(msg, draft[uid])

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "video", content_types=["video"])
def recv_video(msg):
    uid = msg.from_user.id
    draft[uid]["video_id"] = msg.video.file_id
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

# ===================== پاپ‌آپ و لینک =====================
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "popup_text", content_types=["text"])
def recv_popup_text(msg):
    uid = msg.from_user.id
    draft[uid]["popup_text"] = msg.text
    user_state[uid] = "popup_btn_name"
    bot.send_message(msg.chat.id, "🔤 اسم دکمه رو بنویس (مثلاً: 💙 Me?):", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "popup_btn_name", content_types=["text"])
def recv_popup_btn_name(msg):
    uid = msg.from_user.id
    draft[uid]["popup_btn_name"] = msg.text
    user_state[uid] = "confirm"
    show_preview(msg, draft[uid])

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "link_text", content_types=["text"])
def recv_link_text(msg):
    uid = msg.from_user.id
    draft[uid]["link_text"] = msg.text
    user_state[uid] = "link_url"
    bot.send_message(msg.chat.id, "🔗 لینک رو بفرست (https://...):", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "link_url", content_types=["text"])
def recv_link_url(msg):
    uid = msg.from_user.id
    draft[uid]["link_url"] = msg.text
    user_state[uid] = "confirm"
    show_preview(msg, draft[uid])

# ===================== زمان‌بندی =====================
@bot.message_handler(func=lambda m: m.text == "⏰ زمان‌بندی‌ها")
def show_scheduled(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    posts = load_scheduled()
    if not posts:
        bot.send_message(msg.chat.id, "📭 پست زمان‌بندی شده‌ای نداری.", reply_markup=main_menu(uid))
        return
    text = "📋 پست‌های زمان‌بندی شده:\n\n"
    for i, p in enumerate(posts):
        text += f"{i+1}. 📅 {p.get('datetime', p.get('time','?'))} | 📢 {p.get('channel','?')}\n📝 {p['text'][:40]}\n\n"
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🗑 حذف یک پست", callback_data="del_sched_menu"))
    bot.send_message(msg.chat.id, text, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "del_sched_menu")
def cb_del_sched_menu(call):
    uid = call.from_user.id
    posts = load_scheduled()
    mk = types.InlineKeyboardMarkup()
    for i, p in enumerate(posts):
        mk.add(types.InlineKeyboardButton(
            f"🗑 {p.get('datetime', p.get('time','?'))} - {p['text'][:20]}",
            callback_data=f"delsched:{i}"
        ))
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "کدوم پست حذف بشه؟", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delsched:"))
def cb_del_sched(call):
    uid = call.from_user.id
    idx = int(call.data.replace("delsched:", ""))
    posts = load_scheduled()
    if 0 <= idx < len(posts):
        removed = posts.pop(idx)
        try:
            if removed.get("job_id"):
                scheduler.remove_job(removed["job_id"])
        except:
            pass
        save_scheduled(posts)
        bot.answer_callback_query(call.id, "✅ حذف شد")
        bot.send_message(call.message.chat.id, f"✅ پست حذف شد.", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "sched_datetime", content_types=["text"])
def recv_sched_datetime(msg):
    uid = msg.from_user.id
    try:
        dt_str = msg.text.strip()
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        draft[uid]["datetime"] = dt_str
        draft[uid]["sched_dt"] = dt
        posts = load_scheduled()
        posts.append(draft[uid])
        save_scheduled(posts)
        add_schedule_job(draft[uid])
        user_state.pop(uid, None)
        draft.pop(uid, None)
        bot.send_message(
            msg.chat.id,
            f"✅ زمان‌بندی شد!\n📅 {dt_str} (به وقت ایران)",
            reply_markup=main_menu(uid)
        )
    except ValueError:
        bot.send_message(
            msg.chat.id,
            "❌ فرمت اشتباه!\nمثلاً: 2025-07-15 14:30\n(سال-ماه-روز ساعت:دقیقه)",
            reply_markup=back_cancel_kb()
        )

# ===================== پیش‌نمایش =====================
def show_preview(msg, d):
    mk = types.InlineKeyboardMarkup()
    mk.row(
        types.InlineKeyboardButton("💬 پیام", callback_data="add_popup"),
        types.InlineKeyboardButton("🎵 موزیک", callback_data="add_music_link")
    )
    mk.row(types.InlineKeyboardButton("🔗 لینک", callback_data="add_link"))
    mk.row(
        types.InlineKeyboardButton("✏️ ویرایش", callback_data="edit_content"),
        types.InlineKeyboardButton("🔄 از اول", callback_data="restart")
    )
    mk.row(
        types.InlineKeyboardButton("✅ ارسال", callback_data="send"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="cancel")
    )

    preview_text = "👁 پیش‌نمایش:\n\n"
    if d.get("channel"):
        preview_text += f"📢 کانال: {d['channel']}\n"
    if d.get("popup_btn_name"):
        preview_text += f"💬 دکمه: {d['popup_btn_name']}\n"
    if d.get("popup_text"):
        preview_text += f"📝 پیام دکمه: {d['popup_text']}\n"
    if d.get("link_text"):
        preview_text += f"🔗 لینک: {d['link_text']}\n"
    if d.get("audio_id") and d.get("type") == "text":
        preview_text += f"🎵 موزیک: {d.get('music_title','')}\n"

    try:
        if d.get("type") == "text":
            bot.send_message(msg.chat.id, preview_text + f"\n{d.get('text','')}", reply_markup=mk)
        elif d.get("type") == "photo":
            bot.send_photo(msg.chat.id, d["photo_id"], caption=preview_text + d.get("caption", ""), reply_markup=mk)
        elif d.get("type") == "video":
            bot.send_video(msg.chat.id, d["video_id"], caption=preview_text + d.get("caption", ""), reply_markup=mk)
        elif d.get("type") == "music":
            bot.send_message(msg.chat.id, preview_text + f"🎵 {d.get('title','')}", reply_markup=mk)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ خطا در پیش‌نمایش: {e}", reply_markup=main_menu(msg.from_user.id))

# ===================== callback های پیش‌نمایش =====================
@bot.callback_query_handler(func=lambda c: c.data == "add_popup")
def cb_add_popup(call):
    uid = call.from_user.id
    user_state[uid] = "popup_text"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "💬 متن پاپ‌آپ رو بنویس:", reply_markup=back_cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data == "add_link")
def cb_add_link(call):
    uid = call.from_user.id
    user_state[uid] = "link_text"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🔗 اسم دکمه لینک رو بنویس:", reply_markup=back_cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data == "add_music_link")
def cb_add_music_link(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    if draft.get(uid, {}).get("audio_id"):
        bot.send_message(call.message.chat.id, "✅ موزیک قبلاً اضافه شده!")
    else:
        user_state[uid] = "music_for_text"
        bot.send_message(call.message.chat.id, "🎵 فایل موزیک رو بفرست:", reply_markup=back_cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data == "edit_content")
def cb_edit_content(call):
    uid = call.from_user.id
    d = draft.get(uid, {})
    bot.answer_callback_query(call.id)
    t = d.get("type")
    if t == "text":
        user_state[uid] = "text"
        bot.send_message(call.message.chat.id, "📝 متن جدید رو بنویس:", reply_markup=back_cancel_kb())
    elif t == "photo":
        user_state[uid] = "photo"
        bot.send_message(call.message.chat.id, "🖼 عکس جدید رو بفرست:", reply_markup=back_cancel_kb())
    elif t == "video":
        user_state[uid] = "video"
        bot.send_message(call.message.chat.id, "🎬 ویدیو جدید رو بفرست:", reply_markup=back_cancel_kb())
    elif t == "music":
        user_state[uid] = "music"
        bot.send_message(call.message.chat.id, "🎵 فایل موزیک جدید رو بفرست:", reply_markup=back_cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data == "restart")
def cb_restart(call):
    uid = call.from_user.id
    user_state.pop(uid, None)
    draft.pop(uid, None)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🔄 از اول شروع شد.", reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda c: c.data == "send")
def cb_send(call):
    uid = call.from_user.id
    d = draft.get(uid)
    if not d:
        bot.answer_callback_query(call.id, "❌ پستی نیست!")
        return

    # بپرس زمان‌بندی می‌خواد؟
    user_state[uid] = "ask_schedule"
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "⏰ پست رو همین الان ارسال کنم یا زمان‌بندی کنم؟",
        reply_markup=ask_schedule_kb()
    )

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "ask_schedule", content_types=["text"])
def recv_schedule_answer(msg):
    uid = msg.from_user.id
    if msg.text == "✅ همین الان ارسال کن":
        user_state.pop(uid, None)
        do_send(msg.chat.id, uid, draft.get(uid, {}))
    elif msg.text == "⏰ زمان‌بندی کن":
        user_state[uid] = "sched_datetime"
        bot.send_message(
            msg.chat.id,
            "📅 تاریخ و زمان رو بنویس (به وقت ایران):\nفرمت: YYYY-MM-DD HH:MM\nمثلاً: 2025-07-15 14:30",
            reply_markup=back_cancel_kb()
        )
    elif msg.text == "❌ انصراف":
        user_state.pop(uid, None)
        draft.pop(uid, None)
        bot.send_message(msg.chat.id, "❌ انصراف.", reply_markup=main_menu(uid))

def do_send(chat_id, uid, d):
    try:
        music_ch = get_music_channel()
        music_msg = None
        if d.get("audio_id") and d.get("type") in ("text", "photo", "video"):
            music_msg = bot.send_audio(music_ch, d["audio_id"])

        inline_mk = None
        buttons = []
        if d.get("popup_text"):
            btn_name = d.get("popup_btn_name", "💬 Me?")
            popup_id = str(uuid.uuid4())[:8]
            # ذخیره متن پاپ‌آپ با ID
            popups = load_popups()
            popups[popup_id] = d["popup_text"]
            save_popups(popups)
            buttons.append(types.InlineKeyboardButton(btn_name, callback_data=f"pp:{popup_id}"))
        if music_msg:
            music_link = f"https://t.me/{music_ch.replace('@','')}/{music_msg.message_id}"
            buttons.append(types.InlineKeyboardButton("🎵 آهنگ", url=music_link))
        if d.get("link_text") and d.get("link_url"):
            buttons.append(types.InlineKeyboardButton(d["link_text"], url=d["link_url"]))
        if buttons:
            inline_mk = types.InlineKeyboardMarkup()
            inline_mk.row(*buttons)

        target = d.get("channel", "@thelostinwaves")
        if d["type"] == "text":
            bot.send_message(target, d["text"], reply_markup=inline_mk)
        elif d["type"] == "photo":
            bot.send_photo(target, d["photo_id"], caption=d.get("caption", ""), reply_markup=inline_mk)
        elif d["type"] == "video":
            bot.send_video(target, d["video_id"], caption=d.get("caption", ""), reply_markup=inline_mk)
        elif d["type"] == "music":
            bot.send_audio(music_ch, d["audio_id"], caption=d.get("caption", ""), reply_markup=inline_mk)

        draft.pop(uid, None)
        user_state.pop(uid, None)
        bot.send_message(chat_id, "✅ ارسال شد!", reply_markup=main_menu(uid))
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا: {e}", reply_markup=main_menu(uid))
        print(f"Send Error: {e}")

# ===================== پاپ‌آپ با ID =====================
POPUPS_FILE = "popups.json"

def load_popups():
    if not os.path.exists(POPUPS_FILE):
        return {}
    try:
        with open(POPUPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_popups(data):
    try:
        with open(POPUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("pp:"))
def handle_popup(call):
    popup_id = call.data.replace("pp:", "")
    popups = load_popups()
    text = popups.get(popup_id, "...")
    bot.answer_callback_query(call.id, text, show_alert=True)

# ===================== زمان‌بندی خودکار =====================
def send_scheduled_post(post):
    try:
        do_send(None, None, post)
        print(f"✅ پست زمان‌بندی ارسال شد: {post.get('datetime')}")
        posts = load_scheduled()
        posts = [p for p in posts if p.get("job_id") != post.get("job_id")]
        save_scheduled(posts)
    except Exception as e:
        print(f"❌ خطا در ارسال زمان‌بندی: {e}")

def add_schedule_job(post):
    try:
        dt_str = post.get("datetime")
        if not dt_str:
            return
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        dt_iran = dt.replace(tzinfo=IRAN_TZ)
        job_id = post.get("job_id")
        if not job_id:
            job_id = str(uuid.uuid4())
            post["job_id"] = job_id
            posts = load_scheduled()
            for i in range(len(posts)):
                if posts[i].get("datetime") == dt_str and posts[i].get("text") == post.get("text"):
                    posts[i]["job_id"] = job_id
                    break
            save_scheduled(posts)
        scheduler.add_job(
            send_scheduled_post,
            "date",
            run_date=dt_iran,
            id=job_id,
            args=[post],
            replace_existing=True
        )
    except Exception as e:
        print(f"Schedule Error: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cb_cancel(call):
    uid = call.from_user.id
    user_state.pop(uid, None)
    draft.pop(uid, None)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🏠 منو:", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "📊 وضعیت")
def status(msg):
    uid = msg.from_user.id
    if not is_admin(uid): return
    count = len(load_scheduled())
    channels = load_channels()
    ch_list = "\n".join([f"• {c['name']}: {c['username']}" for c in channels])
    bot.send_message(
        msg.chat.id,
        f"📊 وضعیت:\n✅ آنلاین\n\n📺 کانال‌ها:\n{ch_list}\n\n🎵 موزیک: {get_music_channel()}\n⏰ زمان‌بندی: {count} پست\n🕐 زمان ایران: {now_iran()}\n\n👤 ادمین‌ها: {len(load_admins())} نفر",
        reply_markup=main_menu(uid)
    )

for p in load_scheduled():
    add_schedule_job(p)

print("🤖 ربات آماده‌ست!")
print(f"📺 کانال‌ها: {[c['username'] for c in load_channels()]}")
print(f"🎵 موزیک: {get_music_channel()}")
print(f"🕐 زمان ایران: {now_iran()}")

while True:
    try:
        print("🤖 Bot Started")
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except Exception as e:
        print(f"Polling Error: {e}")
        time.sleep(5)
