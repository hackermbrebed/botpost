import os
import json
import logging
import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import Forbidden

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

# Fungsi dan Utilitas Konfigurasi
def get_config():
    """Membaca konfigurasi bot dari config.json."""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Tambahkan welcome_message default jika file tidak ada
        return {"videos": {}, "photo_id": None, "welcome_message": "❌ Anda belum bergabung ke channel kami.\n\nSilakan bergabung ke channel berikut untuk bisa menggunakan bot ini."}

def save_config(config):
    """Menyimpan konfigurasi bot ke config.json."""
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

def get_user_ids():
    """Membaca daftar ID pengguna dari user_ids.json."""
    try:
        with open("user_ids.json", "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_user_ids(user_ids):
    """Menyimpan daftar ID pengguna ke user_ids.json."""
    with open("user_ids.json", "w") as f:
        json.dump(list(user_ids), f)

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

# Handler Perintah Bot (Untuk Semua Pengguna)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /start."""
    # Simpan ID pengguna untuk fitur broadcast
    user_ids = get_user_ids()
    user_ids.add(update.effective_user.id)
    save_user_ids(user_ids)

    config = get_config()
    user_id = update.effective_user.id
    start_parameter = context.args[0] if context.args else None

    is_subscribed, unsubscribed_channels = await check_subscription(context, user_id)
    
    if not is_subscribed:
        # Mengambil pesan dari config.json dan meng-escape-nya
        welcome_message = config.get('welcome_message', '❌ Anda belum bergabung ke channel kami.\n\nSilakan bergabung ke channel berikut untuk bisa menggunakan bot ini.')
        message_text = f"<blockquote>{html.escape(welcome_message)}</blockquote>"
        
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan daftar perintah yang tersedia."""
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID
    
    help_message = "<b>Daftar Perintah Bot:</b>\n\n"
    help_message += "<b>Untuk Semua Pengguna:</b>\n"
    help_message += "<code>/start</code> - Memulai bot dan memeriksa langganan channel.\n"
    help_message += "<code>/help</code> - Menampilkan daftar perintah ini.\n\n"

    if is_admin:
        help_message += "<b>Untuk Admin:</b>\n"
        help_message += "<code>/setwelcome</code> - Mengatur pesan sambutan. Balas dengan teks baru.\n"
        help_message += "<code>/getprofil</code> - Mengatur gambar profil bot. Balas pesan dengan foto.\n"
        help_message += "<code>/addvideo &lt;nama_video&gt;</code> - Menyimpan video. Balas pesan dengan video.\n"
        help_message += "<code>/broadcast</code> - Mengirim pesan broadcast ke semua pengguna. Balas pesan dengan teks/media.\n"
        
    await update.message.reply_text(f"<blockquote>{help_message}</blockquote>", parse_mode=ParseMode.HTML)

# Handler Admin (Perintah khusus Admin)
async def set_welcome_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /setwelcome."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("<blockquote>❌ Perintah ini hanya untuk admin.</blockquote>", parse_mode=ParseMode.HTML)
        return
        
    reply_message = update.message.reply_to_message
    if not reply_message or not reply_message.text:
        await update.message.reply_text("<blockquote>❌ Mohon balas pesan teks yang ingin Anda jadikan pesan sambutan.</blockquote>", parse_mode=ParseMode.HTML)
        return

    new_message = reply_message.text
    config = get_config()
    config["welcome_message"] = new_message
    save_config(config)

    await update.message.reply_text(f"<blockquote>✅ Pesan sambutan berhasil diubah menjadi:\n\n{html.escape(new_message)}</blockquote>", parse_mode=ParseMode.HTML)

async def set_profile_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /getprofil."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("<blockquote>❌ Perintah ini hanya untuk admin.</blockquote>", parse_mode=ParseMode.HTML)
        return
    
    reply_message = update.message.reply_to_message
    if not reply_message or not reply_message.photo:
        await update.message.reply_text("<blockquote>❌ Mohon balas sebuah gambar dengan perintah /getprofil untuk mengatur gambar profil.</blockquote>", parse_mode=ParseMode.HTML)
        return
    file_id = reply_message.photo[-1].file_id
    config = get_config()
    config["photo_id"] = file_id
    save_config(config)
    caption_text = "<blockquote>✅ Gambar profil berhasil diatur!</blockquote>"
    await update.message.reply_photo(photo=file_id, caption=caption_text, parse_mode=ParseMode.HTML)

async def add_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /addvideo."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("<blockquote>❌ Perintah ini hanya untuk admin.</blockquote>", parse_mode=ParseMode.HTML)
        return
        
    reply_message = update.message.reply_to_message
    if not reply_message or not reply_message.video:
        await update.message.reply_text("<blockquote>❌ Mohon balas video dengan perintah /addvideo &lt;nama_video&gt;.</blockquote>", parse_mode=ParseMode.HTML)
        return
    if not context.args:
        await update.message.reply_text("<blockquote>❌ Mohon berikan nama untuk video ini. Contoh: <code>/addvideo video_utama</code></blockquote>", parse_mode=ParseMode.HTML)
        return
    parameter_name = context.args[0]
    file_id = reply_message.video.file_id
    config = get_config()
    config["videos"][parameter_name] = file_id
    save_config(config)
    
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username
    message_text = f"<blockquote>✅ Video <code>{html.escape(parameter_name)}</code> telah disimpan!\nBagikan dengan link: <code>https://t.me/{html.escape(bot_username)}?start={html.escape(parameter_name)}</code></blockquote>"
    await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengirim broadcast ke semua pengguna."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("<blockquote>❌ Perintah ini hanya untuk admin.</blockquote>", parse_mode=ParseMode.HTML)
        return

    reply_message = update.message.reply_to_message
    if not reply_message:
        await update.message.reply_text("<blockquote>❌ Mohon balas pesan yang ingin Anda broadcast.</blockquote>", parse_mode=ParseMode.HTML)
        return

    user_ids = get_user_ids()
    sent_count = 0
    blocked_count = 0
    
    logging.info(f"Memulai broadcast ke {len(user_ids)} pengguna...")

    for user_id in list(user_ids):
        try:
            if reply_message.text:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=reply_message.text,
                    parse_mode=reply_message.parse_mode
                )
            elif reply_message.photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=reply_message.photo[-1].file_id,
                    caption=reply_message.caption,
                    parse_mode=reply_message.parse_mode
                )
            # Tambahkan elif untuk jenis media lain (video, audio, dll.) jika diperlukan
            sent_count += 1
        except Forbidden:
            logging.info(f"Pengguna {user_id} telah memblokir bot. Menghapus dari daftar.")
            user_ids.remove(user_id)
            blocked_count += 1
        except Exception as e:
            logging.error(f"Gagal mengirim pesan ke pengguna {user_id}: {e}")

    save_user_ids(user_ids)
    
    await update.message.reply_text(f"<blockquote>✅ Broadcast selesai!\n\n- Pesan terkirim: {sent_count}\n- Pengguna yang memblokir: {blocked_count}\n\nJumlah pengguna aktif saat ini: {len(user_ids)}</blockquote>", parse_mode=ParseMode.HTML)

# Fungsi Utama
def main():
    """Memulai bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Menambahkan semua handler perintah
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setwelcome", set_welcome_message_handler))
    application.add_handler(CommandHandler("getprofil", set_profile_photo_handler))
    application.add_handler(CommandHandler("addvideo", add_video_handler))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    logging.info("🚀 Bot sedang berjalan...")
    application.run_polling(poll_interval=1)

if __name__ == "__main__":
    main()
