# Copyright (c) 2024 Hacker_Mbrebed
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
GET_POST_MESSAGE, ASK_BUTTONS, GET_BUTTON_DATA, CONFIRM_POSTING = range(4)

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
            "channel_ids": []
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
        await update.message.reply_text("<blockquote>❌ 𝟺𝟶𝟺 𝙽𝚘𝚝 𝙵𝚘𝚞𝚗𝚍</blockquote>", parse_mode=ParseMode.HTML)
        return

    admin_id = update.effective_user.id
    config["admin_ids"].append(admin_id)
    save_config(config)

    await update.message.reply_text("<blockquote>✅ 𝐒𝐞𝐥𝐚𝐦𝐚𝐭! 𝐋𝐮 𝐮𝐝𝐚𝐡 𝐣𝐚𝐝𝐢 𝐚𝐝𝐦𝐢𝐧 𝐬𝐞𝐤𝐚𝐫𝐚𝐧𝐠.\n\n𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘣𝘰𝘵 𝘣𝘺 𝕂𝕒𝕚𝕤𝕒𝕣 𝕌𝕕𝕚𝕟👑</blockquote>", parse_mode=ParseMode.HTML)

async def set_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengatur ID channel tujuan untuk postingan."""
    if not await check_is_admin(update):
        await update.message.reply_text("<blockquote>❌ Perintah ini hanya untuk admin.</blockquote>", parse_mode=ParseMode.HTML)
        return
        
    if not context.args:
        await update.message.reply_text("<blockquote>❌ Mohon sertakan ID channel. Contoh: <code>/setchannel -1001234567890 -100987654321</code></blockquote>", parse_mode=ParseMode.HTML)
        return

    config = get_config()
    new_channel_ids = []
    
    for channel_id_str in context.args:
        try:
            channel_id = int(channel_id_str)
            if channel_id not in config["channel_ids"]:
                config["channel_ids"].append(channel_id)
                new_channel_ids.append(channel_id)

                await context.bot.send_message(
                    chat_id=channel_id,
                    text="<blockquote>✅ Channel ini telah diatur sebagai channel postingan.</blockquote>",
                    parse_mode=ParseMode.HTML
                )
        except (ValueError, BadRequest):
            await update.message.reply_text(f"<blockquote>❌ ID channel tidak valid atau bot tidak memiliki izin posting di sana. Pastikan ID channel diawali dengan <code>-100</code> dan bot adalah admin. ID yang bermasalah: <code>{html.escape(channel_id_str)}</code></blockquote>", parse_mode=ParseMode.HTML)

    if new_channel_ids:
        save_config(config)
        await update.message.reply_text(f"<blockquote>✅ ID channel berikut berhasil disimpan: <code>{', '.join(map(str, new_channel_ids))}</code>. Anda dapat mulai memposting.</blockquote>", parse_mode=ParseMode.HTML)

# --- Fungsi-fungsi ConversationHandler ---
async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai alur posting interaktif."""
    if not await check_is_admin(update):
        await update.message.reply_text("<blockquote>❌ Perintah ini hanya untuk admin.</blockquote>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    config = get_config()
    if not config.get("channel_ids"):
        await update.message.reply_text("<blockquote>❌ Mohon atur ID channel terlebih dahulu dengan perintah <code>/setchannel</code>.</blockquote>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    # Menginisialisasi list untuk menyimpan data tombol
    context.user_data['buttons'] = [None] * 4

    await update.message.reply_text("<blockquote>✍️ Silakan kirim pesan yang akan diposting.</blockquote>", parse_mode=ParseMode.HTML)
    return GET_POST_MESSAGE

async def get_post_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima teks postingan dan meminta detail tombol."""
    if not update.message.text:
        await update.message.reply_text("<blockquote>❌ Mohon kirim teks, bukan media.</blockquote>", parse_mode=ParseMode.HTML)
        return GET_POST_MESSAGE

    context.user_data['message_text'] = update.message.text
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🕹️ 𝐓𝐚𝐦𝐛𝐚𝐡 𝐓𝐨𝐦𝐛𝐨𝐥", callback_data='add_button')],
        [InlineKeyboardButton("⛔ 𝐋𝐚𝐧𝐣𝐮𝐭 𝐓𝐚𝐧𝐩𝐚 𝐓𝐨𝐦𝐛𝐨𝐥", callback_data='no_button')],
        [InlineKeyboardButton("❌ 𝐁𝐚𝐭𝐚𝐥 𝐏𝐨𝐬𝐭", callback_data='cancel_post')]
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
        # Mengubah keyboard untuk menampilkan 4 pilihan tombol dalam layout 2x2
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("𝐓𝐨𝐦𝐛𝐨𝐥 𝟏", callback_data='button_1'),
             InlineKeyboardButton("𝐓𝐨𝐦𝐛𝐨𝐥 𝟐", callback_data='button_2')],
            [InlineKeyboardButton("𝐓𝐨𝐦𝐛𝐨𝐥 𝟑", callback_data='button_3'),
             InlineKeyboardButton("𝐓𝐨𝐦𝐛𝐨𝐥 𝟒", callback_data='button_4')],
            [InlineKeyboardButton("🅺🅾🅽🅵🅸🆁🅼🅰🆂🅸", callback_data='final_confirm')]
        ])
        await query.edit_message_text(
            "<blockquote>Pilih tombol yang ingin Anda atur.</blockquote>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return ASK_BUTTONS
    
    elif choice == 'no_button':
        # Langsung konfirmasi dan posting tanpa tombol
        return await confirm_post(update, context, has_button=False)
        
    elif choice == 'cancel_post':
        return await cancel_post(update, context)

    # Menangani pilihan tombol dan beralih ke state GET_BUTTON_DATA
    elif choice.startswith('button_'):
        button_index = int(choice.split('_')[1]) - 1
        context.user_data['current_button_index'] = button_index
        await query.edit_message_text(
            f"<blockquote>✍️ Silakan kirim teks dan URL untuk tombol {button_index + 1} dalam format ini:\n\n<code>Teks Tombol | https://www.url.com</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return GET_BUTTON_DATA
    
    # Menangani tombol "Lanjut ke Konfirmasi" yang memicu pratinjau
    elif choice == 'final_confirm':
        # Membangun keyboard untuk pratinjau
        final_keyboard_buttons = []
        for btn in context.user_data['buttons']:
            if btn:
                final_keyboard_buttons.append(InlineKeyboardButton(btn['text'], url=btn['url']))
        
        # Tombol konfirmasi akhir
        confirm_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ 𝐘𝐚, 𝐏𝐨𝐬𝐭!", callback_data='final_confirm_post')],
            [InlineKeyboardButton("❌ 𝐁𝐚𝐭𝐚𝐥𝐤𝐚𝐧", callback_data='cancel_post')]
        ])
        
        # Membangun keyboard pratinjau dalam tata letak 2x2
        preview_keyboard_rows = []
        for i in range(0, len(final_keyboard_buttons), 2):
            preview_keyboard_rows.append(final_keyboard_buttons[i:i+2])
        
        preview_keyboard = InlineKeyboardMarkup(preview_keyboard_rows) if preview_keyboard_rows else None

        try:
            await query.edit_message_text(
                "<blockquote>✅ Pratinjau postingan:</blockquote>",
                parse_mode=ParseMode.HTML
            )
            # Mengirim pratinjau pesan dengan tombol
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"<blockquote>{html.escape(context.user_data['message_text'])}</blockquote>",
                reply_markup=preview_keyboard,
                parse_mode=ParseMode.HTML
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="<blockquote>Apakah Anda yakin ingin memposting ini?</blockquote>",
                reply_markup=confirm_keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logging.error(f"Gagal menampilkan pratinjau: {e}")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"<blockquote>❌ Gagal menampilkan pratinjau. Error: {html.escape(str(e))}</blockquote>",
                parse_mode=ParseMode.HTML
            )
        
        return CONFIRM_POSTING

async def get_button_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima teks dan URL tombol, lalu kembali ke menu tombol."""
    try:
        data = update.message.text.split('|', 1)
        if len(data) != 2:
            raise ValueError
        
        button_text = data[0].strip()
        button_url = data[1].strip()

        button_index = context.user_data.get('current_button_index')
        context.user_data['buttons'][button_index] = {'text': button_text, 'url': button_url}

        # Menampilkan pratinjau tombol yang sudah diatur
        final_keyboard_buttons = []
        for btn in context.user_data['buttons']:
            if btn:
                final_keyboard_buttons.append(InlineKeyboardButton(btn['text'], url=btn['url']))

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("𝐓𝐨𝐦𝐛𝐨𝐥 𝟏", callback_data='button_1'),
             InlineKeyboardButton("𝐓𝐨𝐦𝐛𝐨𝐥 𝟐", callback_data='button_2')],
            [InlineKeyboardButton("𝐓𝐨𝐦𝐛𝐨𝐥 𝟑", callback_data='button_3'),
             InlineKeyboardButton("𝐓𝐨𝐦𝐛𝐨𝐥 𝟒", callback_data='button_4')],
            [InlineKeyboardButton("🅺🅾🅽🅵🅸🆁🅼🅰🆂🅸", callback_data='final_confirm')]
        ])

        await update.message.reply_text(
            "<blockquote>✅ Data tombol berhasil disimpan. Pilih tombol lain atau lanjut ke konfirmasi.</blockquote>",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        return ASK_BUTTONS
    except (ValueError, IndexError):
        await update.message.reply_text(
            "<blockquote>❌ Format tidak valid. Mohon kirim dalam format: <code>Teks | URL</code></blockquote>",
            parse_mode=ParseMode.HTML
        )
        return GET_BUTTON_DATA


async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengonfirmasi dan memposting pesan ke channel."""
    query = update.callback_query
    await query.answer()

    config = get_config()
    channel_ids = config.get("channel_ids", [])

    message_to_post = f"<blockquote>{html.escape(context.user_data['message_text'])}</blockquote>"
    
    buttons = context.user_data.get('buttons', [])
    final_buttons = [InlineKeyboardButton(btn['text'], url=btn['url']) for btn in buttons if btn]
    
    # Membuat tata letak 2x2 untuk tombol
    keyboard_rows = []
    for i in range(0, len(final_buttons), 2):
        keyboard_rows.append(final_buttons[i:i+2])
    keyboard = InlineKeyboardMarkup(keyboard_rows)

    try:
        if not channel_ids:
             raise ValueError("Tidak ada ID channel yang diatur. Mohon gunakan perintah <i>/setchannel</i> terlebih dahulu.")

        for channel_id in channel_ids:
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
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("<blockquote>✅ Postingan dibatalkan.</blockquote>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani perintah /start untuk menampilkan panduan."""
    message = "<blockquote><b>📢 𝐒𝐞𝐥𝐚𝐦𝐚𝐭 𝐝𝐚𝐭𝐚𝐧𝐠! 𝐁𝐨𝐭 𝐢𝐧𝐢 𝐦𝐞𝐦𝐛𝐚𝐧𝐭𝐮 𝐀𝐧𝐝𝐚 𝐦𝐞𝐦𝐩𝐨𝐬𝐭𝐢𝐧𝐠 𝐤𝐞 𝐜𝐡𝐚𝐧𝐧𝐞𝐥.\n\n📄 𝙋𝙖𝙣𝙙𝙪𝙖𝙣 :</b></blockquote>\n"
    message += "👤 𝐀𝐭𝐮𝐫 𝐝𝐢𝐫𝐢 𝐀𝐧𝐝𝐚 𝐬𝐞𝐛𝐚𝐠𝐚𝐢 𝐚𝐝𝐦𝐢𝐧 𝐝𝐞𝐧𝐠𝐚𝐧 <i>/setup</i>.\n⚙️ 𝐀𝐭𝐮𝐫 𝐜𝐡𝐚𝐧𝐧𝐞𝐥 𝐩𝐨𝐬𝐭𝐢𝐧𝐠𝐚𝐧 𝐝𝐞𝐧𝐠𝐚𝐧 <i>/setchannel ID_CHANNEL</i>.\n✍️ 𝐌𝐮𝐥𝐚𝐢 𝐩𝐫𝐨𝐬𝐞𝐬 𝐩𝐨𝐬𝐭𝐢𝐧𝐠 𝐝𝐞𝐧𝐠𝐚𝐧 <i>/post</i>.\n🔥 𝐈𝐤𝐮𝐭𝐢 𝐢𝐧𝐬𝐭𝐫𝐮𝐤𝐬𝐢 𝐲𝐚𝐧𝐠 𝐝𝐢𝐛𝐞𝐫𝐢𝐤𝐚𝐧 𝐛𝐨𝐭.\n\n<blockquote>𝘗𝘰𝘸𝘦𝘳𝘦𝘥 𝘣𝘰𝘵 𝘣𝘺 𝕂𝕒𝕚𝕤𝕒𝕣 𝕌𝕕𝕚𝕟👑</blockquote>"
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
            ASK_BUTTONS: [CallbackQueryHandler(handle_button_choice)],
            GET_BUTTON_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_button_data)],
            CONFIRM_POSTING: [
                CallbackQueryHandler(confirm_post, pattern='^final_confirm_post$'),
                CallbackQueryHandler(cancel_post, pattern='^cancel_post$')
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_post)],
    )

    application.add_handler(CommandHandler("setup", setup_command))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("setchannel", set_channel_id))

    logging.info("🚀 Bot sedang berjalan...")
    application.run_polling(poll_interval=1)

if __name__ == "__main__":
    main()
