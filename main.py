import os
import json
import logging
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from dotenv import load_dotenv
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL1_ID = os.getenv("CHANNEL1_ID")
CHANNEL1_LINK = os.getenv("CHANNEL1_LINK")
CHANNEL2_ID = os.getenv("CHANNEL2_ID")
CHANNEL2_LINK = os.getenv("CHANNEL2_LINK")

if not all([API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, CHANNEL1_ID, CHANNEL1_LINK, CHANNEL2_ID, CHANNEL2_LINK]):
    logging.error("❌ Pastikan semua variabel diisi di file .env.")
    exit()

try:
    ADMIN_ID = int(ADMIN_ID.strip())
    CHANNEL1_ID = int(CHANNEL1_ID.strip())
    CHANNEL2_ID = int(CHANNEL2_ID.strip())
except (ValueError, TypeError):
    logging.error("❌ ADMIN_ID, CHANNEL1_ID, atau CHANNEL2_ID tidak valid. Pastikan itu adalah angka.")
    exit()

app = Client(
    "fsub_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

def get_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"videos": {}, "photo_id": None}

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

async def check_subscription(client, user_id):
    channels_to_check = [
        {"id": CHANNEL1_ID, "link": CHANNEL1_LINK},
        {"id": CHANNEL2_ID, "link": CHANNEL2_LINK}
    ]
    unsubscribed_channels = []
    
    for channel in channels_to_check:
        try:
            member = await client.get_chat_member(chat_id=channel['id'], user_id=user_id)
            if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                unsubscribed_channels.append(channel)
        except Exception as e:
            logging.error(f"Error saat memeriksa langganan di channel {channel['id']}: {e}")
            unsubscribed_channels.append(channel)
    
    return len(unsubscribed_channels) == 0, unsubscribed_channels

@app.on_message(filters.user(ADMIN_ID) & filters.private & filters.command("getprofil", prefixes="/"))
async def set_profile_photo_handler(client, message):
    reply_message = message.reply_to_message
    if not reply_message or not reply_message.photo:
        await message.reply_text("❌ Reply gambar dan kirim perintah /getprofil untuk mengatur gambar profilnya nyet!")
        return
    file_id = reply_message.photo.file_id
    config = get_config()
    config["photo_id"] = file_id
    save_config(config)
    await message.reply_photo(photo=file_id, caption="> ✅ Gambar profil berhasil diatur nyet!", parse_mode='markdown')

@app.on_message(filters.user(ADMIN_ID) & filters.private & filters.command("addvideo", prefixes="/"))
async def add_video_handler(client, message):
    reply_message = message.reply_to_message
    if not reply_message or not reply_message.video:
        await message.reply_text("> ❌ Reply videonya dengan perintah ini nyett /addvideo <nama_video>.", parse_mode='markdown')
        return
    if len(message.command) < 2:
        await message.reply_text("> ❌ Kasih nama untuk videonya nyett. Contoh: `/addvideo video_utama`", parse_mode='markdown')
        return
    parameter_name = message.command[1]
    file_id = reply_message.video.file_id
    config = get_config()
    config["videos"][parameter_name] = file_id
    save_config(config)
    await message.reply_text(f"> ✅ Video `{parameter_name}` telah disimpan! "
                             f"\n> Bagikan dengan link: `https://t.me/{client.me.username}?start={parameter_name}`", parse_mode='markdown')

@app.on_message(filters.command("start", prefixes="/"))
async def start_command(client, message):
    config = get_config()
    user_id = message.from_user.id
    start_parameter = message.command[1] if len(message.command) > 1 else None
    
    is_subscribed, unsubscribed_channels = await check_subscription(client, user_id)
    
    if not is_subscribed:
        pesan = "> ❌ Lu belum join ke channelnya nyett.\n\n> Join dulu biar gw bisa kirim videonya **GOBLOG**."
        keyboard_buttons = []
        for channel in unsubscribed_channels:
            if channel['id'] == CHANNEL1_ID:
                keyboard_buttons.append([InlineKeyboardButton("Gabung Channel 1", url=CHANNEL1_LINK)])
            elif channel['id'] == CHANNEL2_ID:
                keyboard_buttons.append([InlineKeyboardButton("Gabung Channel 2", url=CHANNEL2_LINK)])
        
        coba_lagi_link = f"https://t.me/{client.me.username}?start={start_parameter or ''}"
        keyboard_buttons.append([InlineKeyboardButton("Coba Lagi", url=coba_lagi_link)])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        photo_id = config.get("photo_id")
        
        if photo_id:
            await message.reply_photo(photo=photo_id, caption=pesan, reply_markup=keyboard, parse_mode='markdown')
        else:
            await message.reply_text(pesan, reply_markup=keyboard, parse_mode='markdown')
    else:
        video_list = config.get("videos", {})
        
        if not start_parameter:
            await message.reply_text("> ✅ Lu udah join. Sekarang gunakan link /start dengan parameter yang valid nyett.", parse_mode='markdown')
            return

        video_to_send = video_list.get(start_parameter)

        if video_to_send:
            try:
                await message.reply_video(video=video_to_send, caption="> ✅ Nontonnya sambil ngocok ya nyett awokaowk.", parse_mode='markdown')
            except Exception as e:
                await message.reply_text(f"> ❌ Terjadi eror nyett pada videonya: {e}", parse_mode='markdown')
        else:
            await message.reply_text("> ✅ Lu udah join. Tapi, parameter video tidak valid.", parse_mode='markdown')

@app.on_message(filters.command("myid", prefixes="/"))
async def my_id_command(client, message):
    user_id = message.from_user.id
    await message.reply_text(f"> User ID Anda adalah: `{user_id}`", parse_mode='markdown')

if __name__ == "__main__":
    logging.info("🚀 Bot sedang berjalan...")
    app.run()
