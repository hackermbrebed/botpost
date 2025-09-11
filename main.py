# Copyright (c) 2024 Nama_Anda
#
# This script is licensed under the MIT License.
# See the LICENSE file for details.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import json
import logging
import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

# Memuat variabel lingkungan dari file .env
from dotenv import load_dotenv
load_dotenv()

# Mengambil token bot dari variabel lingkungan
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Mendefinisikan status untuk ConversationHandler
GET_POST_MESSAGE, ASK_BUTTONS, GET_BUTTON_TEXT, GET_BUTTON_LINK, CONFIRM_POSTING = range(5)

# --- Utilitas dan Konfigurasi ---
def get_config():
    """Membaca konfigurasi bot dari bot_config.json."""
    try:
        with open("bot_config.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Mengembalikan struktur default jika file tidak ada atau rusak
        return {
            "admin_ids": [],
            "channel_id": None
        }

def save_config(config):
    """Menyimpan konfigurasi bot ke bot_config.json."""
    with open("bot_config.json", "w") as f:
        json.dump(config, f, indent=4)

async def check_is_admin(update: Update):
    """Memeriksa apakah pengguna yang menjalankan perintah adalah admin."""
    config = get_config()
    return update.effective_user.id in config.get("admin_ids", [])

# --- Handler Perintah Admin ---
async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /setup untuk mengatur admin pertama."""
    config = get_config()
    if config["admin_ids"]:
        await update.message.reply_text("<blockquote>❌ Bot sudah diatur. Perintah ini hanya bisa digunakan sekali.</blockquote>", parse_mode=ParseMode.HTML)
        return

    admin_id = update.effective_user.id
    config["admin_ids"].append(admin_id)
    save_config(config)

    await update.message.reply_text("<blockquote>✅ Pengaturan bot berhasil! Anda adalah admin sekarang.</blockquote>", parse_mode=ParseMode.HTML)

async def set_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengatur ID channel tujuan untuk postingan."""
    if not await check_is_admin(update):
        await update.message.reply_text("<blockquote>❌ Perintah ini hanya untuk admin.</blockquote>", parse_mode=ParseMode.HTML)
        return
        
    if not context.args:
        await update.message.reply_text("<blockquote>❌ Mohon sertakan ID channel. Contoh: <code>/setchannel -1001234567890</code></blockquote>", parse_mode=ParseMode.HTML)
        return

    channel_id_str = context.args[0]
    try:
        channel_id = int(channel_id_str)
        config = get_config()
        config["channel_id"] = channel_id
        save_config(config)

        await context.bot.send_message(
            chat_id=channel_id,
            text="<blockquote>✅ Channel ini telah diatur sebagai channel postingan.</blockquote>",
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_text("<blockquote>✅ ID channel berhasil disimpan. Anda dapat mulai memposting.</blockquote>", parse_mode=ParseMode.HTML)
    except (ValueError, BadRequest):
        await update.message.reply_text("<blockquote>❌ ID channel tidak valid atau bot tidak memiliki izin posting di sana. Pastikan ID channel diawali dengan <code>-100</code> dan bot adalah admin.</blockquote>", parse_mode=ParseMode.HTML)

# --- Fungsi-fungsi ConversationHandler ---
async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai alur posting interaktif."""
    if not await check_is_admin(update):
        await update.message.reply_text("<blockquote>❌ Perintah ini hanya untuk admin.</blockquote>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    config = get_config()
    if not config.get("channel_id"):
        await update.message.reply_text("<blockquote>❌ Mohon atur ID channel terlebih dahulu dengan perintah <code>/setchannel</code>.</blockquote>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    await update.message.reply_text("<blockquote>✍️ Silakan kirim pesan yang akan diposting.</blockquote>", parse_mode=ParseMode.HTML)
    return GET_POST_MESSAGE

async def get_post_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima teks postingan dan meminta detail tombol."""
    if not update.message.text:
        await update.message.reply_text("<blockquote>❌ Mohon kirim teks, bukan media.</blockquote>", parse_mode=ParseMode.HTML)
        return GET_POST_MESSAGE

    context.user_data['message_text'] = update.message.text

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tambah Tombol", callback_data='add_button')],
        [InlineKeyboardButton("Lanjut Tanpa Tombol", callback_data='no_button')],
        [InlineKeyboardButton("❌ Batalkan", callback_data='cancel_post')]
    ])
    
    await update.message.reply_text(
        "<blockquote>Pesan berhasil disimpan. Sekarang pilih salah satu opsi.</blockquote>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    return ASK_BUTTONS

async def handle_button_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan pengguna untuk menambah tombol atau tidak."""
    query = update.callback_query
    await query.answer()

    choice = query.data
    
    if choice == 'add_button':
        await query.edit_message_text(
            "<blockquote>✍️ Silakan kirim teks untuk tombol.</blockquote>",
            parse_mode=ParseMode.HTML
        )
        return GET_BUTTON_TEXT
    
    elif choice == 'no_button':
        # Langsung konfirmasi dan posting tanpa tombol
        await confirm_post(update, context, has_button=False)
        return ConversationHandler.END
        
    elif choice == 'cancel_post':
        return await cancel_post(update, context)

async def get_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima teks tombol dari pengguna."""
    if not update.message.text:
        await update.message.reply_text("<blockquote>❌ Mohon kirim teks yang valid.</blockquote>", parse_mode=ParseMode.HTML)
        return GET_BUTTON_TEXT

    context.user_data['button_text'] = update.message.text
    await update.message.reply_text(
        "<blockquote>🔗 Bagus. Sekarang kirimkan URL untuk tombol.</blockquote>",
        parse_mode=ParseMode.HTML
    )
    return GET_BUTTON_LINK

async def get_button_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima URL tombol dan menampilkan pratinjau dengan tombol konfirmasi."""
    button_url = update.message.text
    context.user_data['button_url'] = button_url

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Ya, Post!", callback_data='final_confirm')],
        [InlineKeyboardButton("Batalkan", callback_data='cancel_post')]
    ])
    
    preview_message = f"<blockquote>✅ Pratinjau postingan:</blockquote>\n"
    preview_message += f"{html.escape(context.user_data['message_text'])}"

    await update.message.reply_text(
        preview_message,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(context.user_data['button_text'], url=button_url)]]),
        parse_mode=ParseMode.HTML
    )
    await update.message.reply_text(
        "<blockquote>Apakah Anda yakin ingin memposting ini?</blockquote>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    return CONFIRM_POSTING

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE, has_button=True):
    """Mengonfirmasi dan memposting pesan ke channel."""
    query = update.callback_query
    await query.answer()

    config = get_config()
    channel_id = config.get("channel_id")

    message_to_post = f"<blockquote>{html.escape(context.user_data['message_text'])}</blockquote>"
    
    keyboard = None
    if has_button:
        button_text = context.user_data['button_text']
        button_url = context.user_data['button_url']
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url)]])

    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text=message_to_post,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await query.edit_message_text("<blockquote>✅ Postingan berhasil dikirim ke channel.</blockquote>", parse_mode=ParseMode.HTML)
    except Exception as e:
        logging.error(f"Gagal memposting ke channel: {e}")
        await query.edit_message_text(f"<blockquote>❌ Gagal memposting. Mohon cek ID channel atau izin bot. Error: {html.escape(str(e))}</blockquote>", parse_mode=ParseMode.HTML)
    
    return ConversationHandler.END

async def cancel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membatalkan alur posting."""
    if isinstance(update.callback_query, type(None)):
        await update.message.reply_text("<blockquote>✅ Postingan dibatalkan.</blockquote>", parse_mode=ParseMode.HTML)
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("<blockquote>✅ Postingan dibatalkan.</blockquote>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /start untuk menampilkan panduan."""
    message = "<blockquote><b>📢 Selamat datang! Bot ini membantu Anda memposting ke channel.\n\n📄 Panduan :</b></blockquote>\n"
    message += "<blockquote>👤 Atur diri Anda sebagai admin dengan <i>/setup</i>.\n⚙️ Atur channel postingan dengan <i>/setchannel &lt;ID_CHANNEL&gt;</i>.\n✍️ Mulai proses posting dengan <i>/post</i>.\n🔥 Ikuti petunjuk interaktif yang diberikan bot melalui tombol.</blockquote>\n"
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


# --- Fungsi Utama ---
def main():
    """Memulai bot."""
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN tidak ditemukan. Mohon atur di file .env.")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("post", start_post)],
        states={
            GET_POST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_post_message)],
            ASK_BUTTONS: [CallbackQueryHandler(handle_button_choice, pattern='^add_button$|^no_button$|^cancel_post$')],
            GET_BUTTON_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_button_text)],
            GET_BUTTON_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_button_link)],
            CONFIRM_POSTING: [CallbackQueryHandler(confirm_post, pattern='^final_confirm$')],
        },
        fallbacks=[CommandHandler("cancel", cancel_post), CallbackQueryHandler(cancel_post, pattern='^cancel_post$')],
    )

    application.add_handler(CommandHandler("setup", setup_command))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("setchannel", set_channel_id))

    logging.info("🚀 Bot sedang berjalan...")
    application.run_polling(poll_interval=1)

if __name__ == "__main__":
    main()
