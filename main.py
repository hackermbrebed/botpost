import os
import telebot
from telebot import types
from dotenv import load_dotenv # Tambahkan ini untuk membaca .env

# Muat variabel lingkungan dari file .env (akan digunakan di lingkungan lokal/VPS)
load_dotenv() 

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if BOT_TOKEN is None:
    print("Error: BOT_TOKEN environment variable not set.")
    print("Please set BOT_TOKEN in Replit Secrets (if using Replit) or .env file (if using local/VPS).")
    exit()

CHANNEL_ID_1_STR = os.environ.get("CHANNEL_ID_1")
if CHANNEL_ID_1_STR is None:
    print("Error: CHANNEL_ID_1 environment variable not set.")
    print("Please set CHANNEL_ID_1 in Replit Secrets or .env file.")
    exit()
try:
    CHANNEL_ID_1 = int(CHANNEL_ID_1_STR)
except ValueError:
    print("Error: CHANNEL_ID_1 in Secrets/environment is not a valid integer. Please check it.")
    exit()

CHANNEL_LINK_1 = os.environ.get("CHANNEL_LINK_1")
if CHANNEL_LINK_1 is None:
    print("Error: CHANNEL_LINK_1 environment variable not set.")
    print("Please set CHANNEL_LINK_1 in Replit Secrets or .env file.")
    exit()

CHANNEL_ID_2_STR = os.environ.get("CHANNEL_ID_2")
if CHANNEL_ID_2_STR is None:
    print("Error: CHANNEL_ID_2 environment variable not set.")
    print("Please set CHANNEL_ID_2 in Replit Secrets or .env file.")
    exit()
try:
    CHANNEL_ID_2 = int(CHANNEL_ID_2_STR)
except ValueError:
    print("Error: CHANNEL_ID_2 in Secrets/environment is not a valid integer. Please check it.")
    exit()

CHANNEL_LINK_2 = os.environ.get("CHANNEL_LINK_2")
if CHANNEL_LINK_2 is None:
    print("Error: CHANNEL_LINK_2 environment variable not set.")
    print("Please set CHANNEL_LINK_2 in Replit Secrets or .env file.")
    exit()

VIDEO_FILE_ID = "BAACAgUAAxkBAAOgaHFLByzycQ_KIcd5BWCnmm6dEhAAAgYZAAJFh4hXnxzRz-vhr9o2BA"  
bot = telebot.TeleBot(BOT_TOKEN)

def is_member(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except telebot.apihelper.ApiTelegramException as e:
        if "Bad Request: chat not found" in str(e):
            print(f"Error: Channel ID {chat_id} not found or bot is not an admin there. Please check CHANNEL_ID in Secrets/environment.")
        elif "User not found" in str(e):
            pass  
        else:
            print(f"Error checking membership for user {user_id} in chat {chat_id}: {e}")
        return False  

@bot.message_handler(commands=['start'])
def send_welcome_and_video(message):
    user_id = message.from_user.id
    username = message.from_user.first_name if message.from_user.first_name else "Pengguna"  

    member_of_channel_1 = is_member(CHANNEL_ID_1, user_id)
    member_of_channel_2 = is_member(CHANNEL_ID_2, user_id)

    if not member_of_channel_1 or not member_of_channel_2:
        markup = types.InlineKeyboardMarkup()
        if not member_of_channel_1:
            join_button_1 = types.InlineKeyboardButton("Channel Mas Jawa", url=CHANNEL_LINK_1)
            markup.add(join_button_1)
            print(f"Pengguna {username} ({user_id}) belum bergabung ke Channel Mas Jawa.")

        if not member_of_channel_2:
            join_button_2 = types.InlineKeyboardButton("Channel Nyai Jawa", url=CHANNEL_LINK_2)
            markup.add(join_button_2)
            print(f"Pengguna {username} ({user_id}) belum bergabung ke Channel Nyai Jawa.")

        bot.send_message(
            message.chat.id,
            "Untuk menggunakan bot ini, Anda harus bergabung ke channel berikut terlebih dahulu, kalau sudah klik /start kembali:",
            reply_markup=markup
        )
        return  

    try:
        if VIDEO_FILE_ID == "BAACAgUAAxkBAAOgaHFLByzycQ_KIcd5BWCnmm6dEhAAAgYZAAJFh4hXnxzRz-vhr9o2BA":  
            bot.send_video(
                message.chat.id,
                video=VIDEO_FILE_ID,
                caption=f"Halo {username}! Selamat datang di bot kami!\n"
                            "Enjoy aja nontonnya."
            )
            print(f"Mengirim video dari File ID '{VIDEO_FILE_ID}' ke {username} ({user_id}).")
        else:
            bot.send_message(
                message.chat.id,
                f"Halo {username}! Selamat datang di bot kami!\n"
                "Video belum diatur dengan benar."
            )
            print("Peringatan: VIDEO_FILE_ID mungkin tidak terdeteksi dengan benar.")

    except telebot.apihelper.ApiTelegramException as e:
        print(f"Error saat mengirim video dari File ID '{VIDEO_FILE_ID}': {e}")
        bot.send_message(
            message.chat.id,
            f"Halo {username}! Selamat datang di bot kami! (Maaf, video perkenalan tidak dapat dikirim. Error: {e})"
        )
    except Exception as e:
        print(f"Error tak terduga saat mengirim video: {e}")
        bot.send_message(
            message.chat.id,
            f"Halo {username}! Selamat datang di bot kami! (Maaf, terjadi error tak terduga saat mengirim video.)"
        )

    # Pesan ini akan selalu terkirim setelah video (atau error video) jika sudah subscribe
    bot.send_message(
        message.chat.id,
        "Anda sudah menjadi anggota kedua channel. Selamat datang!\n"
        "Gunakan fitur bot kami sekarang."
    )

if __name__ == '__main__':
    print("Bot Fsub dengan dua channel (menggunakan File ID) sedang berjalan...")
    bot.polling(none_stop=True)
