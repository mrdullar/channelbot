import telebot
import json
import os
import time
import uuid
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

TOKEN = "8829999667:AAG719Vnp9bf9Mw99JDrZDQyweBXN-h_E2Y"
MUSIC_CHANNEL = "@acmmf"
OWNER_IDS = [8305135192, 8316171820]  # فقط این دو نفر می‌تونن ادمین مدیریت کنن

bot = telebot.TeleBot(TOKEN)
bot.delete_webhook()
scheduler = BackgroundScheduler()
scheduler.start()

SCHED_FILE = "scheduled.json"
CHANNELS_FILE = "channels.json"
ADMINS_FILE = "admins.json"
user_state = {}
draft = {}

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

def is_owner(uid):
    return uid in OWNER_IDS

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

def is_admin(uid):
    return uid in load_admins()

def main_menu(uid=None):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("📝 پست متنی", "🖼 پست با عکس")
    m.row("🎬 پست با ویدیو", "🎵 ارسال موزیک")
    m.row("⏰ زمان‌بندی", "📋 لیست زمان‌بندی")
    m.row("🗑 حذف زمان‌بندی", "📺 مدیریت کانال‌ها")
    if uid and is_owner(uid):
        m.row("👥 مدیریت ادمین‌ها")
    m.row("📊 وضعیت")
    return m

def channel_select_menu():
    channels = load_channels()
    mk = types.InlineKeyboardMarkup()
    for ch in channels:
        mk.add(types.InlineKeyboardButton(f"📢 {ch['name']} ({ch['username']})", callback_data=f"selch:{ch['username']}"))
    return mk

def back_cancel_kb():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("⬅️ برگشت", "❌ انصراف")
    return mk

# ===================== شروع =====================
@bot.message_handler(commands=["start"])
def start(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ دسترسی ندارید.")
        return
    channels = load_channels()
    ch_list = "\n".join([f"• {c['name']}: {c['username']}" for c in channels])
    bot.send_message(msg.chat.id, f"👋 سلام!\n\n📺 کانال‌ها:\n{ch_list}\n\n🎵 موزیک: {MUSIC_CHANNEL}", reply_markup=main_menu(msg.from_user.id))

@bot.message_handler(func=lambda m: m.text == "❌ انصراف")
def cancel(msg):
    uid = msg.from_user.id
    user_state.pop(uid, None)
    draft.pop(uid, None)
    bot.send_message(msg.chat.id, "❌ انصراف.", reply_markup=main_menu(msg.from_user.id))

# ===================== برگشت به عقب =====================
STATE_FLOW = {
    "music_for_text": "ask_music",
    "ask_music": "text",
    "sched_time": "sched_text",
    "popup_btn_name": "popup_text",
    "link_url": "link_text",
}

@bot.message_handler(func=lambda m: m.text == "⬅️ برگشت")
def go_back(msg):
    uid = msg.from_user.id
    current = user_state.get(uid)
    if not current:
        bot.send_message(msg.chat.id, "🏠 منو:", reply_markup=main_menu(msg.from_user.id))
        return

    if current == "text":
        user_state[uid] = "select_channel_text"
        bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())
        return
    if current == "ask_music":
        user_state[uid] = "text"
        bot.send_message(msg.chat.id, "📝 متن پست رو دوباره بنویس:", reply_markup=back_cancel_kb())
        return
    if current == "music_for_text":
        user_state[uid] = "ask_music"
        mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
        mk.row("✅ بله", "❌ خیر")
        mk.row("⬅️ برگشت", "❌ انصراف")
        bot.send_message(msg.chat.id, "🎵 موزیک هم اضافه کنی؟", reply_markup=mk)
        return
    if current == "sched_text":
        user_state[uid] = "select_channel_sched"
        bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())
        return
    if current == "sched_time":
        user_state[uid] = "sched_text"
        bot.send_message(msg.chat.id, "📝 متن پست رو دوباره بنویس:", reply_markup=back_cancel_kb())
        return
    if current == "popup_text":
        user_state[uid] = "confirm"
        show_preview(msg, draft[uid])
        return
    if current == "popup_btn_name":
        user_state[uid] = "popup_text"
        bot.send_message(msg.chat.id, "💬 متن پاپ‌آپ رو دوباره بنویس:", reply_markup=back_cancel_kb())
        return
    if current == "link_text":
        user_state[uid] = "confirm"
        show_preview(msg, draft[uid])
        return
    if current == "link_url":
        user_state[uid] = "link_text"
        bot.send_message(msg.chat.id, "🔗 اسم دکمه لینک رو دوباره بنویس:", reply_markup=back_cancel_kb())
        return

    bot.send_message(msg.chat.id, "🏠 منو:", reply_markup=main_menu(msg.from_user.id))
    user_state.pop(uid, None)

# ===================== مدیریت کانال =====================
@bot.message_handler(func=lambda m: m.text == "📺 مدیریت کانال‌ها")
def manage_channels(msg):
    if not is_admin(msg.from_user.id): return
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
    bot.send_message(msg.chat.id, "🔗 یوزرنیم کانال رو بنویس (مثلاً: @channelname):", reply_markup=back_cancel_kb())

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
    bot.send_message(msg.chat.id, f"✅ کانال «{username}» اضافه شد!", reply_markup=main_menu(msg.from_user.id))

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
    idx = int(call.data.replace("rmch:", ""))
    channels = load_channels()
    if 0 <= idx < len(channels):
        removed = channels.pop(idx)
        save_channels(channels)
        bot.answer_callback_query(call.id, f"✅ {removed['name']} حذف شد")
        bot.send_message(call.message.chat.id, f"✅ کانال «{removed['name']}» حذف شد.", reply_markup=main_menu(call.from_user.id))
    else:
        bot.answer_callback_query(call.id, "❌ خطا")

# ===================== مدیریت ادمین‌ها (فقط مالکین اصلی) =====================
@bot.message_handler(func=lambda m: m.text == "👥 مدیریت ادمین‌ها")
def manage_admins(msg):
    uid = msg.from_user.id
    if not is_owner(uid):
        bot.send_message(msg.chat.id, "❌ فقط ادمین‌های اصلی دسترسی دارن.", reply_markup=main_menu(uid))
        return
    admins = load_admins()
    text = "👥 ادمین‌های فعلی:\n\n"
    for i, a in enumerate(admins):
        tag = " 👑 (اصلی)" if a in OWNER_IDS else ""
        text += f"{i+1}. {a}{tag}\n"
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
    bot.send_message(call.message.chat.id, "🆔 آیدی عددی کاربر جدید رو بنویس:\n(می‌تونه از @userinfobot بگیره)", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "add_admin_id", content_types=["text"])
def recv_admin_id(msg):
    uid = msg.from_user.id
    if not is_owner(uid):
        return
    try:
        new_id = int(msg.text.strip())
        admins = load_admins()
        if new_id in admins:
            bot.send_message(msg.chat.id, "⚠️ این کاربر از قبل ادمینه.", reply_markup=main_menu(uid))
        else:
            admins.append(new_id)
            save_admins(admins)
            bot.send_message(msg.chat.id, f"✅ کاربر {new_id} به عنوان ادمین اضافه شد!\n(فقط شما می‌تونید ادمین حذف/اضافه کنید، این ادمین جدید نمی‌تونه)", reply_markup=main_menu(uid))
        user_state.pop(uid, None)
    except ValueError:
        bot.send_message(msg.chat.id, "❌ آیدی باید عدد باشه. دوباره بنویس:", reply_markup=back_cancel_kb())

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
    admins = load_admins()
    if target_id in OWNER_IDS:
        bot.answer_callback_query(call.id, "❌ ادمین اصلی قابل حذف نیست!")
        return
    if target_id in admins:
        admins.remove(target_id)
        save_admins(admins)
        bot.answer_callback_query(call.id, "✅ حذف شد")
        bot.send_message(call.message.chat.id, f"✅ ادمین {target_id} حذف شد.", reply_markup=main_menu(uid))
    else:
        bot.answer_callback_query(call.id, "❌ پیدا نشد")


# ===================== پست متنی =====================
@bot.message_handler(func=lambda m: m.text == "📝 پست متنی")
def text_post(msg):
    if not is_admin(msg.from_user.id): return
    channels = load_channels()
    if not channels:
        bot.send_message(msg.chat.id, "❌ هیچ کانالی ثبت نشده!", reply_markup=main_menu(msg.from_user.id))
        return
    user_state[msg.from_user.id] = "select_channel_text"
    draft[msg.from_user.id] = {"type": "text"}
    bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())

@bot.callback_query_handler(func=lambda c: c.data.startswith("selch:"))
def cb_select_channel(call):
    uid = call.from_user.id
    channel = call.data.replace("selch:", "")
    if uid not in draft:
        draft[uid] = {}
    draft[uid]["channel"] = channel
    bot.answer_callback_query(call.id)

    state = user_state.get(uid, "")

    if state == "select_channel_text":
        user_state[uid] = "text"
        bot.send_message(call.message.chat.id, "📝 متن پست رو بنویس:", reply_markup=back_cancel_kb())
    elif state == "select_channel_photo":
        user_state[uid] = "photo"
        bot.send_message(call.message.chat.id, "🖼 عکس رو بفرست:", reply_markup=back_cancel_kb())
    elif state == "select_channel_video":
        user_state[uid] = "video"
        bot.send_message(call.message.chat.id, "🎬 ویدیو رو بفرست:", reply_markup=back_cancel_kb())
    elif state == "select_channel_sched":
        user_state[uid] = "sched_text"
        bot.send_message(call.message.chat.id, "⏰ متن پست رو بنویس:", reply_markup=back_cancel_kb())

# ===================== پست عکس =====================
@bot.message_handler(func=lambda m: m.text == "🖼 پست با عکس")
def photo_post(msg):
    if not is_admin(msg.from_user.id): return
    channels = load_channels()
    if not channels:
        bot.send_message(msg.chat.id, "❌ هیچ کانالی ثبت نشده!", reply_markup=main_menu(msg.from_user.id))
        return
    user_state[msg.from_user.id] = "select_channel_photo"
    draft[msg.from_user.id] = {"type": "photo"}
    bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())

# ===================== پست ویدیو =====================
@bot.message_handler(func=lambda m: m.text == "🎬 پست با ویدیو")
def video_post(msg):
    if not is_admin(msg.from_user.id): return
    channels = load_channels()
    if not channels:
        bot.send_message(msg.chat.id, "❌ هیچ کانالی ثبت نشده!", reply_markup=main_menu(msg.from_user.id))
        return
    user_state[msg.from_user.id] = "select_channel_video"
    draft[msg.from_user.id] = {"type": "video"}
    bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "video", content_types=["video"])
def recv_video(msg):
    uid = msg.from_user.id
    draft[uid]["video_id"] = msg.video.file_id
    draft[uid]["caption"] = msg.caption or ""
    user_state[uid] = "confirm"
    show_preview(msg, draft[uid])

# ===================== موزیک مستقل =====================
@bot.message_handler(func=lambda m: m.text == "🎵 ارسال موزیک")
def music_post(msg):
    if not is_admin(msg.from_user.id): return
    user_state[msg.from_user.id] = "music"
    draft[msg.from_user.id] = {"type": "music"}
    bot.send_message(msg.chat.id, "🎵 فایل موزیک رو بفرست:", reply_markup=back_cancel_kb())

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

# ===================== زمان‌بندی =====================
@bot.message_handler(func=lambda m: m.text == "⏰ زمان‌بندی")
def sched_post(msg):
    if not is_admin(msg.from_user.id): return
    channels = load_channels()
    if not channels:
        bot.send_message(msg.chat.id, "❌ هیچ کانالی ثبت نشده!", reply_markup=main_menu(msg.from_user.id))
        return
    user_state[msg.from_user.id] = "select_channel_sched"
    draft[msg.from_user.id] = {"type": "scheduled"}
    bot.send_message(msg.chat.id, "📺 کدوم کانال؟", reply_markup=channel_select_menu())

@bot.message_handler(func=lambda m: m.text == "📋 لیست زمان‌بندی")
def list_sched(msg):
    if not is_admin(msg.from_user.id): return
    posts = load_scheduled()
    if not posts:
        bot.send_message(msg.chat.id, "📭 پست زمان‌بندی شده‌ای نداری.", reply_markup=main_menu(msg.from_user.id))
        return
    text = "📋 پست‌های زمان‌بندی شده:\n\n"
    for i, p in enumerate(posts):
        text += f"{i+1}. ⏰ {p['time']} | 📺 {p.get('channel','?')}\n📝 {p['text'][:40]}\n\n"
    bot.send_message(msg.chat.id, text, reply_markup=main_menu(msg.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🗑 حذف زمان‌بندی")
def del_sched(msg):
    if not is_admin(msg.from_user.id): return
    posts = load_scheduled()
    if not posts:
        bot.send_message(msg.chat.id, "📭 پست زمان‌بندی شده‌ای نداری.", reply_markup=main_menu(msg.from_user.id))
        return
    user_state[msg.from_user.id] = "delete_sched"
    text = "🗑 شماره پست رو بنویس:\n\n"
    for i, p in enumerate(posts):
        text += f"{i+1}. ⏰ {p['time']} - {p['text'][:30]}\n"
    bot.send_message(msg.chat.id, text, reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: m.text == "📊 وضعیت")
def status(msg):
    if not is_admin(msg.from_user.id): return
    count = len(load_scheduled())
    channels = load_channels()
    ch_list = "\n".join([f"• {c['name']}: {c['username']}" for c in channels])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    bot.send_message(msg.chat.id, f"📊 وضعیت:\n✅ آنلاین\n\n📺 کانال‌ها:\n{ch_list}\n\n🎵 موزیک: {MUSIC_CHANNEL}\n⏰ زمان‌بندی: {count} پست\n🕐 {now}\n\n👤 ادمین‌ها: {len(load_admins())} نفر", reply_markup=main_menu(msg.from_user.id))

# ===================== دریافت متن/عکس/ویدیو =====================
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

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "sched_text", content_types=["text"])
def recv_sched_text(msg):
    uid = msg.from_user.id
    draft[uid]["text"] = msg.text
    user_state[uid] = "sched_time"
    bot.send_message(msg.chat.id, "⏰ زمان رو بنویس (مثلاً 14:30):", reply_markup=back_cancel_kb())

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
        bot.send_message(msg.chat.id, f"✅ زمان‌بندی شد برای {msg.text.strip()}!", reply_markup=main_menu(msg.from_user.id))
    except ValueError:
        bot.send_message(msg.chat.id, "❌ فرمت اشتباه! مثلاً: 14:30", reply_markup=back_cancel_kb())

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "delete_sched", content_types=["text"])
def recv_del_num(msg):
    uid = msg.from_user.id
    try:
        num = int(msg.text.strip()) - 1
        posts = load_scheduled()
        if 0 <= num < len(posts):
            removed = posts.pop(num)
            try:
                if removed.get("job_id"):
                    scheduler.remove_job(removed["job_id"])
            except:
                pass
            save_scheduled(posts)
            user_state.pop(uid, None)
            bot.send_message(msg.chat.id, f"✅ پست {removed['time']} حذف شد.", reply_markup=main_menu(msg.from_user.id))
        else:
            bot.send_message(msg.chat.id, "❌ شماره معتبر نیست.")
    except ValueError:
        bot.send_message(msg.chat.id, "❌ عدد بنویس.")

# ===================== پاپ‌آپ و لینک =====================
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "popup_text", content_types=["text"])
def recv_popup_text(msg):
    uid = msg.from_user.id
    if len(msg.text.encode('utf-8')) > 50:
        bot.send_message(msg.chat.id, "❌ متن خیلی طولانیه! حداکثر حدود ۳۰-۴۰ کاراکتر فارسی بنویس و دوباره امتحان کن:", reply_markup=back_cancel_kb())
        return
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

# ===================== پیش‌نمایش =====================
def show_preview(msg, d):
    mk = types.InlineKeyboardMarkup()
    mk.row(
        types.InlineKeyboardButton("💬 پیام", callback_data="add_popup"),
        types.InlineKeyboardButton("🎵 موزیک", callback_data="add_music_link")
    )
    mk.row(types.InlineKeyboardButton("🔗 لینک", callback_data="add_link"))
    mk.row(
        types.InlineKeyboardButton("✏️ ویرایش متن", callback_data="edit_text"),
        types.InlineKeyboardButton("🔄 شروع دوباره", callback_data="restart")
    )
    mk.row(
        types.InlineKeyboardButton("✅ ارسال", callback_data="send"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="cancel")
    )
    preview_text = "👁 پیش‌نمایش:\n\n"
    if d.get("channel"):
        preview_text += f"📺 کانال: {d['channel']}\n"
    if d.get("popup_btn_name"):
        preview_text += f"💬 دکمه: {d['popup_btn_name']}\n"
    if d.get("popup_text"):
        preview_text += f"📝 پیام دکمه: {d['popup_text']}\n"
    if d.get("link_text"):
        preview_text += f"🔗 دکمه لینک: {d['link_text']}\n"
    if d.get("audio_id") and d["type"] == "text":
        preview_text += f"🎵 موزیک: {d.get('music_title','')}\n"

    if d["type"] == "text":
        bot.send_message(msg.chat.id, preview_text + f"\n{d['text']}", reply_markup=mk)
    elif d["type"] == "photo":
        bot.send_photo(msg.chat.id, d["photo_id"], caption=preview_text + d.get("caption", ""), reply_markup=mk)
    elif d["type"] == "video":
        bot.send_video(msg.chat.id, d["video_id"], caption=preview_text + d.get("caption", ""), reply_markup=mk)
    elif d["type"] == "music":
        bot.send_message(msg.chat.id, preview_text + f"🎵 {d.get('title','')}", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "edit_text")
def cb_edit_text(call):
    uid = call.from_user.id
    d = draft.get(uid, {})
    bot.answer_callback_query(call.id)
    if d.get("type") == "text":
        user_state[uid] = "text"
        bot.send_message(call.message.chat.id, "📝 متن جدید رو بنویس:", reply_markup=back_cancel_kb())
    elif d.get("type") == "photo":
        user_state[uid] = "photo"
        bot.send_message(call.message.chat.id, "🖼 عکس جدید رو بفرست:", reply_markup=back_cancel_kb())
    elif d.get("type") == "video":
        user_state[uid] = "video"
        bot.send_message(call.message.chat.id, "🎬 ویدیو جدید رو بفرست:", reply_markup=back_cancel_kb())
    elif d.get("type") == "music":
        user_state[uid] = "music"
        bot.send_message(call.message.chat.id, "🎵 فایل موزیک جدید رو بفرست:", reply_markup=back_cancel_kb())

@bot.callback_query_handler(func=lambda c: c.data == "restart")
def cb_restart(call):
    uid = call.from_user.id
    user_state.pop(uid, None)
    draft.pop(uid, None)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🔄 از اول شروع شد.", reply_markup=main_menu(call.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data == "add_popup")
def cb_add_popup(call):
    uid = call.from_user.id
    user_state[uid] = "popup_text"
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "💬 متن پاپ‌آپ رو بنویس (کوتاه، حدود ۳۰-۴۰ کاراکتر):", reply_markup=back_cancel_kb())

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

@bot.callback_query_handler(func=lambda c: c.data == "send")
def cb_send(call):
    uid = call.from_user.id
    d = draft.get(uid)
    if not d:
        bot.answer_callback_query(call.id, "❌ پستی نیست!")
        return
    try:
        target_channel = d.get("channel", MUSIC_CHANNEL)

        music_msg = None
        if d.get("audio_id") and d["type"] in ("text", "photo", "video"):
            music_msg = bot.send_audio(MUSIC_CHANNEL, d["audio_id"])

        inline_mk = None
        buttons = []
        if d.get("popup_text"):
            btn_name = d.get("popup_btn_name", "💬 Me?")
            popup = d["popup_text"][:50]
            buttons.append(types.InlineKeyboardButton(btn_name, callback_data=f"popup:{popup}"))
        if music_msg:
            music_link = f"https://t.me/{MUSIC_CHANNEL.replace('@','')}/{music_msg.message_id}"
            buttons.append(types.InlineKeyboardButton("🎵 آهنگ", url=music_link))
        if d.get("link_text") and d.get("link_url"):
            buttons.append(types.InlineKeyboardButton(d["link_text"], url=d["link_url"]))
        if buttons:
            inline_mk = types.InlineKeyboardMarkup()
            inline_mk.row(*buttons)

        if d["type"] == "text":
            bot.send_message(target_channel, d["text"], reply_markup=inline_mk)
        elif d["type"] == "photo":
            bot.send_photo(target_channel, d["photo_id"], caption=d.get("caption", ""), reply_markup=inline_mk)
        elif d["type"] == "video":
            bot.send_video(target_channel, d["video_id"], caption=d.get("caption", ""), reply_markup=inline_mk)
        elif d["type"] == "music":
            bot.send_audio(MUSIC_CHANNEL, d["audio_id"], caption=d.get("caption", ""), reply_markup=inline_mk)

        bot.edit_message_text("✅ ارسال شد!", call.message.chat.id, call.message.message_id) if d["type"] == "text" else None
        if d["type"] != "text":
            bot.send_message(call.message.chat.id, "✅ ارسال شد!")
        user_state.pop(uid, None)
        draft.pop(uid, None)
        bot.send_message(call.message.chat.id, "🏠 منو:", reply_markup=main_menu(call.from_user.id))
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا: {e}")
        print(f"Send Error: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cb_cancel(call):
    uid = call.from_user.id
    user_state.pop(uid, None)
    draft.pop(uid, None)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🏠 منو:", reply_markup=main_menu(call.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("popup:"))
def handle_popup(call):
    text = call.data.replace("popup:", "")
    bot.answer_callback_query(call.id, text, show_alert=True)

def send_scheduled(post_text, channel):
    try:
        bot.send_message(channel, post_text)
        print("✅ پست زمان‌بندی ارسال شد")
    except Exception as e:
        print(f"❌ خطا: {e}")

def add_schedule_job(post):
    h, m = post["time"].split(":")
    job_id = post.get("job_id")
    channel = post.get("channel", "@thelostinwaves")
    if not job_id:
        job_id = str(uuid.uuid4())
        post["job_id"] = job_id
        posts = load_scheduled()
        for i in range(len(posts)):
            if posts[i]["time"] == post["time"] and posts[i]["text"] == post["text"]:
                posts[i]["job_id"] = job_id
                break
        save_scheduled(posts)
    scheduler.add_job(send_scheduled, "cron", id=job_id, hour=int(h), minute=int(m), args=[post["text"], channel], replace_existing=True)

for p in load_scheduled():
    add_schedule_job(p)

print("🤖 ربات آماده‌ست!")
channels_init = load_channels()
print(f"📺 کانال‌ها: {[c['username'] for c in channels_init]}")
print(f"🎵 موزیک: {MUSIC_CHANNEL}")
print(f"👤 ادمین‌ها: {load_admins()}")

while True:
    try:
        print("🤖 Bot Started")
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except Exception as e:
        print(f"Polling Error: {e}")
        time.sleep(5)
