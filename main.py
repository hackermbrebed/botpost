import os
import json
import logging
import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Memuat variabel dari file .env
from dotenv import load_dotenv
load_dotenv()

# Mengambil token bot dan ID dari variabel lingkungan
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL1_ID = os.getenv("CHANNEL1_ID")
CHANNEL1_LINK = os.getenv("CHANNEL1_LINK")
CHANNEL2_ID = os.getenv("CHANNEL2_ID")
CHANNEL2_LINK = os.getenv("CHANNEL2_LINK")

# Validasi variabel lingkungan
if not all([BOT_TOKEN, ADMIN_ID, CHANNEL1_ID, CHANNEL1_LINK, CHANNEL2_ID, CHANNEL2_LINK]):
    logging.error("❌ Pastikan semua variabel diisi di file .env.")
    exit()

try:
    ADMIN_ID = int(ADMIN_ID.strip())
    CHANNEL1_ID = int(CHANNEL1_ID.strip())
    CHANNEL2_ID = int(CHANNEL2_ID.strip())
except (ValueError, TypeError):
    logging.error("❌ ADMIN_ID, CHANNEL1_ID, atau CHANNEL2_ID tidak valid. Pastikan itu adalah angka.")
    exit()

# ---
## Fungsi dan Utilitas Konfigurasi

def get_config():
    """Membaca konfigurasi bot dari config.json."""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"videos": {}, "photo_id": None}

def save_config(config):
    """Menyimpan konfigurasi bot ke config.json."""
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Memeriksa apakah pengguna berlangganan ke saluran yang diperlukan."""
    channels_to_check = [
        {"id": CHANNEL1_ID, "link": CHANNEL1_LINK},
        {"id": CHANNEL2_ID, "link": CHANNEL2_LINK}
    ]
    unsubscribed_channels = []

    for channel in channels_to_check:
        try:
            member: ChatMember = await context.bot.get_chat_member(chat_id=channel['id'], user_id=user_id)
            if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                unsubscribed_channels.append(channel)
        except Exception as e:
            logging.error(f"Error checking subscription for channel {channel['id']}: {e}")
            unsubscribed_channels.append(channel)

    return len(unsubscribed_channels) == 0, unsubscribed_channels

# ---
## Handler Perintah Bot (Untuk Pengguna)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /start."""
    config = get_config()
    user_id = update.effective_user.id
    start_parameter = context.args[0] if context.args else None

    is_subscribed, unsubscribed_channels = await check_subscription(context, user_id)
    
    if not is_subscribed:
        # Menggunakan \n sebagai ganti <br> untuk menghindari error parsing
        message_text = "<blockquote>❌ Anda belum bergabung ke channel kami.\n\nSilakan bergabung ke channel berikut untuk bisa menggunakan bot ini.</blockquote>"
        keyboard_buttons = []
        for channel in unsubscribed_channels:
            if channel['id'] == CHANNEL1_ID:
                keyboard_buttons.append([InlineKeyboardButton("Gabung Channel 1", url=CHANNEL1_LINK)])
            elif channel['id'] == CHANNEL2_ID:
                keyboard_buttons.append([InlineKeyboardButton("Gabung Channel 2", url=CHANNEL2_LINK)])
        
        coba_lagi_link = f"https://t.me/{context.bot.username}?start={start_parameter or ''}"
        keyboard_buttons.append([InlineKeyboardButton("Coba Lagi", url=coba_lagi_link)])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        photo_id = config.get("photo_id")
        
        if photo_id:
            await update.message.reply_photo(photo=photo_id, caption=message_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(message_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        video_list = config.get("videos", {})
        
        if not start_parameter:
            await update.message.reply_text("<blockquote>✅ Anda sudah bergabung. Gunakan link /start dengan parameter yang valid.</blockquote>", parse_mode=ParseMode.HTML)
            return

        video_to_send = video_list.get(start_parameter)

        if video_to_send:
            try:
                caption_text = "<blockquote>✅ Selamat datang! Anda berhasil bergabung ke channel.</blockquote>"
                await update.message.reply_video(video=video_to_send, caption=caption_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                await update.message.reply_text(f"<blockquote>❌ Terjadi kesalahan saat mengirim video: {html.escape(str(e))}</blockquote>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("<blockquote>✅ Anda sudah bergabung. Namun, parameter video tidak valid.</blockquote>", parse_mode=ParseMode.HTML)

# ---
## Handler Admin (Teks Sederhana, TANPA parse_mode)

async def set_profile_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /getprofil."""
    if update.effective_user.id != ADMIN_ID:
        return
    
    reply_message = update.message.reply_to_message
    if not reply_message or not reply_message.photo:
        await update.message.reply_text("Mohon balas sebuah gambar dengan perintah /getprofil untuk mengatur gambar profil.")
        return
    file_id = reply_message.photo[-1].file_id
    config = get_config()
    config["photo_id"] = file_id
    save_config(config)
    caption_text = "Gambar profil berhasil diatur!"
    await update.message.reply_photo(photo=file_id, caption=caption_text)

async def add_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /addvideo."""
    if update.effective_user.id != ADMIN_ID:
        return
        
    reply_message = update.message.reply_to_message
    if not reply_message or not reply_message.video:
        await update.message.reply_text("Mohon balas video dengan perintah /addvideo <nama_video>.")
        return
    if not context.args:
        await update.message.reply_text("Mohon berikan nama untuk video ini. Contoh: /addvideo video_utama")
        return
    parameter_name = context.args[0]
    file_id = reply_message.video.file_id
    config = get_config()
    config["videos"][parameter_name] = file_id
    save_config(config)
    
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username
    message_text = f"Video {parameter_name} telah disimpan.\nBagikan dengan link: https://t.me/{bot_username}?start={parameter_name}"
    await update.message.reply_text(message_text)

async def my_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /myid."""
    user_id = update.effective_user.id
    message_text = f"User ID Anda adalah: {user_id}"
    await update.message.reply_text(message_text)

# ---
## Fungsi Utama

def main():
    """Memulai bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Menambahkan semua handler perintah
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("getprofil", set_profile_photo_handler))
    application.add_handler(CommandHandler("addvideo", add_video_handler))
    application.add_handler(CommandHandler("myid", my_id_command))

    logging.info("🚀 Bot sedang berjalan...")
    application.run_polling(poll_interval=1)

if __name__ == "__main__":
    main()
