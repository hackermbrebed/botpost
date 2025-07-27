import os
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import asyncio

# Impor fungsi database yang kita buat
from video_db import add_video, get_all_videos, init_db, \
                     add_managed_group, remove_managed_group, \
                     is_group_managed, get_managed_groups, \
                     set_config, get_config # Import fungsi konfigurasi baru

# Muat variabel dari .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
# FORCE_SUB_CHANNEL_ID = int(os.getenv("FORCE_SUB_CHANNEL_ID")) # Hapus baris ini dari .env
ADMIN_ID = int(os.getenv("ADMIN_ID")) # ID Telegram Anda

# Inisialisasi bot Pyrogram
app = Client(
    "fsub_video_bot_session", # Nama sesi bot Anda
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Inisialisasi Database
init_db()

# --- Fungsi Utility ---
async def get_fsub_channel_id():
    """Mengambil ID channel Force Subscribe dari database."""
    fsub_id_str = get_config("FORCE_SUB_CHANNEL_ID")
    if fsub_id_str:
        return int(fsub_id_str)
    return None # Mengembalikan None jika belum diatur

async def is_subscribed(client, user_id):
    """
    Fungsi untuk memeriksa apakah pengguna sudah subscribe channel atau belum.
    """
    fsub_channel_id = await get_fsub_channel_id()
    if not fsub_channel_id:
        # Jika channel fsub belum diatur, anggap tidak subscribe dan minta admin setting
        return False

    try:
        member = await client.get_chat_member(fsub_channel_id, user_id)
        if member.status in ["member", "creator", "administrator"]:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking subscription for user {user_id}: {e}")
        return False

async def get_channel_link(client, channel_id):
    """
    Mendapatkan link channel/grup dari ID.
    """
    try:
        chat = await client.get_chat(channel_id)
        if chat.invite_link:
            return chat.invite_link
        elif chat.username:
            return f"https://t.me/{chat.username}"
        else:
            return f"https://t.me/c/{str(channel_id)[4:]}"
    except Exception as e:
        print(f"Error getting channel link for {channel_id}: {e}")
        return "https://t.me/"

# --- Middleware untuk Cek Admin ---
def admin_only(func):
    async def wrapper(client, message):
        if message.from_user.id != ADMIN_ID:
            await message.reply_text("Maaf, hanya admin bot yang bisa menggunakan perintah ini.")
            return
        await func(client, message)
    return wrapper

# --- Middleware untuk Cek Grup yang Dikelola ---
async def check_managed_group(client, message):
    if message.chat.type in ["group", "supergroup"]:
        if not is_group_managed(message.chat.id):
            await message.reply_text("Maaf, grup ini tidak dikelola oleh bot. Admin perlu menggunakan `/manage_this_group` di sini.")
            return False
    return True

# --- Handler untuk Pesan Normal (Jika FSub Channel Belum Diatur) ---
async def check_fsub_channel_set(client, message):
    fsub_channel_id = await get_fsub_channel_id()
    if not fsub_channel_id and message.from_user.id != ADMIN_ID:
        await message.reply_text("Bot belum dikonfigurasi sepenuhnya. Mohon tunggu admin untuk mengatur channel Force Subscribe dengan perintah `/set_fsub_channel <ID_CHANNEL>`.")
        return False
    elif not fsub_channel_id and message.from_user.id == ADMIN_ID and not message.text.startswith("/set_fsub_channel"): # Cek agar tidak looping saat admin coba set
         await message.reply_text("Channel Force Subscribe belum diatur. Mohon gunakan perintah `/set_fsub_channel <ID_CHANNEL>` untuk mengaturnya.")
         return False
    return True


# --- Handlers Bot ---

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client, message):
    if not await check_fsub_channel_set(client, message):
        return

    user_id = message.from_user.id
    fsub_channel_id = await get_fsub_channel_id()
    channel_link = await get_channel_link(client, fsub_channel_id)

    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel Untuk Nonton", url=channel_link)]
        ])
        await message.reply_text(
            "Halo! 👋 Untuk menonton video, Anda harus bergabung ke channel ini terlebih dahulu:",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    await message.reply_text(
        "Selamat datang! Anda sudah bergabung dengan channel. "
        "Sekarang Anda bisa melihat video-video yang saya bagikan.\n\n"
        "Gunakan perintah /videos untuk melihat daftar video."
    )

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client, message):
    if not await check_managed_group(client, message):
        return
    if not await check_fsub_channel_set(client, message):
        return

    user_id = message.from_user.id
    fsub_channel_id = await get_fsub_channel_id()
    channel_link = await get_channel_link(client, fsub_channel_id)

    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel Untuk Nonton", url=channel_link)]
        ])
        await message.reply_text(
            f"Halo {message.from_user.mention}! 👋 Untuk menonton video di grup ini, Anda harus bergabung ke channel ini terlebih dahulu:",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    await message.reply_text(
        f"Selamat datang {message.from_user.mention}! Anda sudah bergabung dengan channel. "
        "Sekarang Anda bisa menggunakan perintah /videos di sini."
    )

@app.on_message(filters.command("videos") & filters.private)
async def list_videos_private_command(client, message):
    if not await check_fsub_channel_set(client, message):
        return

    user_id = message.from_user.id
    fsub_channel_id = await get_fsub_channel_id()
    channel_link = await get_channel_link(client, fsub_channel_id)

    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel Untuk Nonton", url=channel_link)]
        ])
        await message.reply_text(
            "Maaf, Anda harus bergabung ke channel ini terlebih dahulu untuk melihat daftar video.",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    videos = get_all_videos()
    if not videos:
        await message.reply_text("Belum ada video yang dibagikan oleh admin.")
        return

    await message.reply_text("Mengirimkan video-video yang tersedia, mohon tunggu...")
    for file_id, caption in videos:
        try:
            await client.send_video(
                chat_id=user_id,
                video=file_id,
                caption=caption if caption else "Video dari admin."
            )
            await asyncio.sleep(0.5) # Jeda sebentar agar tidak terkena flood limit
        except Exception as e:
            await message.reply_text(f"Gagal mengirim video: {e}")
            print(f"Error sending video {file_id} to {user_id}: {e}")
    await message.reply_text("Semua video telah dikirim.")


@app.on_message(filters.command("videos") & filters.group)
async def list_videos_group_command(client, message):
    if not await check_managed_group(client, message):
        return
    if not await check_fsub_channel_set(client, message):
        return

    user_id = message.from_user.id
    fsub_channel_id = await get_fsub_channel_id()
    channel_link = await get_channel_link(client, fsub_channel_id)

    if not await is_subscribed(client, user_id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Gabung Channel Untuk Nonton", url=channel_link)]
        ])
        await message.reply_text(
            "Maaf, Anda harus bergabung ke channel ini terlebih dahulu untuk melihat daftar video.",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return

    videos = get_all_videos()
    if not videos:
        await message.reply_text("Belum ada video yang dibagikan oleh admin.")
        return

    await message.reply_text("Mengirimkan video-video yang tersedia di grup ini, mohon tunggu...")
    for file_id, caption in videos:
        try:
            await client.send_video(
                chat_id=message.chat.id, # Kirim ke grup
                video=file_id,
                caption=caption if caption else "Video dari admin."
            )
            await asyncio.sleep(0.5)
        except Exception as e:
            await message.reply_text(f"Gagal mengirim video di grup: {e}")
            print(f"Error sending video {file_id} to group {message.chat.id}: {e}")
    await message.reply_text("Semua video telah dikirim.")


@app.on_message(filters.video & filters.private)
@admin_only
async def handle_new_video(client, message):
    video_file_id = message.video.file_id
    video_caption = message.caption if message.caption else None

    add_video(video_file_id, video_caption)
    await message.reply_text(f"Video berhasil disimpan! File ID: `{video_file_id}`\n\nVideo ini akan otomatis dibagikan kepada pengguna setelah mereka bergabung channel.")

# --- Perintah Konfigurasi Grup (Hanya untuk Admin Bot) ---

@app.on_message(filters.command("manage_this_group") & filters.group)
@admin_only
async def manage_group(client, message):
    group_id = message.chat.id
    group_title = message.chat.title

    if add_managed_group(group_id):
        await message.reply_text(f"Grup **{group_title}** (`{group_id}`) berhasil ditambahkan ke daftar grup yang dikelola bot. Sekarang, bot akan menerapkan Force Subscribe di grup ini.")
    else:
        await message.reply_text(f"Grup **{group_title}** (`{group_id}`) sudah ada dalam daftar grup yang dikelola.")

@app.on_message(filters.command("unmanage_this_group") & filters.group)
@admin_only
async def unmanage_group(client, message):
    group_id = message.chat.id
    group_title = message.chat.title

    if remove_managed_group(group_id):
        await message.reply_text(f"Grup **{group_title}** (`{group_id}`) berhasil dihapus dari daftar grup yang dikelola bot. Bot tidak akan lagi menerapkan Force Subscribe di grup ini.")
    else:
        await message.reply_text(f"Grup **{group_title}** (`{group_id}`) tidak ditemukan dalam daftar grup yang dikelola.")

@app.on_message(filters.command("list_managed_groups") & filters.private)
@admin_only
async def list_managed_groups(client, message):
    managed_groups = get_managed_groups()
    if not managed_groups:
        await message.reply_text("Belum ada grup yang dikelola oleh bot.")
        return

    response = "Daftar Grup yang Dikelola:\n"
    for group_id in managed_groups:
        try:
            chat = await client.get_chat(group_id)
            response += f"- **{chat.title}** (`{group_id}`)\n"
        except Exception:
            response += f"- Grup Tidak Dikenal (`{group_id}` - Mungkin sudah dihapus?)\n"
    await message.reply_text(response)

# --- Perintah Konfigurasi Channel Force Subscribe (Hanya untuk Admin Bot) ---

@app.on_message(filters.command("set_fsub_channel") & filters.private)
@admin_only
async def set_fsub_channel_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("Penggunaan: `/set_fsub_channel <ID_CHANNEL>`\nContoh: `/set_fsub_channel -1001234567890`")
        return

    channel_id_str = message.command[1]
    try:
        channel_id = int(channel_id_str)
        # Coba cek apakah bot admin di channel tersebut
        try:
            chat = await client.get_chat(channel_id)
            if chat.type not in ["channel", "supergroup"]:
                await message.reply_text("ID yang Anda berikan bukan ID channel atau supergroup yang valid.")
                return

            # Cek apakah bot adalah admin di channel tersebut
            bot_member = await client.get_chat_member(channel_id, client.me.id)
            if bot_member.status not in ["administrator", "creator"]:
                await message.reply_text("Bot harus menjadi **Administrator** di channel/grup Force Subscribe yang Anda atur, dengan izin `Invite Users` dan `Get Chat Member Info`.")
                return

            set_config("FORCE_SUB_CHANNEL_ID", str(channel_id))
            await message.reply_text(f"Channel Force Subscribe berhasil diatur ke **{chat.title}** (`{channel_id}`).")

        except Exception as e:
            await message.reply_text(f"Gagal memverifikasi channel. Pastikan ID benar dan bot adalah admin di channel tersebut. Error: {e}")
            print(f"Error verifying FSub channel: {e}")
            return

    except ValueError:
        await message.reply_text("ID channel harus berupa angka. Contoh: `-1001234567890`")
        return

@app.on_message(filters.command("get_fsub_channel") & filters.private)
@admin_only
async def get_fsub_channel_command(client, message):
    fsub_channel_id = await get_fsub_channel_id()
    if fsub_channel_id:
        try:
            chat = await client.get_chat(fsub_channel_id)
            await message.reply_text(f"Channel Force Subscribe saat ini adalah: **{chat.title}** (`{fsub_channel_id}`).")
        except Exception:
            await message.reply_text(f"Channel Force Subscribe saat ini adalah: `{fsub_channel_id}` (Tidak dapat mengambil nama channel).")
    else:
        await message.reply_text("Channel Force Subscribe belum diatur.")


# Jalankan bot
async def main():
    print("Memulai bot FSub Video multi-grup dan konfigurasi channel...")
    await app.start()
    print("Bot FSub Video multi-grup dan konfigurasi channel berjalan.")
    await idle() # Biarkan bot tetap berjalan sampai dihentikan secara manual
    print("Bot FSub Video multi-grup dan konfigurasi channel berhenti.")
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
