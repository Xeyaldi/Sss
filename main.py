import os
import heroku3
import asyncio
import random
import string
import requests
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

# Sabit MongoDB Linkin
MONGO_URL = "mongodb+srv://cabbarovxeyal32_db_user:Xeyal032aze@cluster0.f3gogmg.mongodb.net/?appName=Cluster0" 
# GitHub Reponun Tarball Linki (Herokunun ən sevdiyi format)
REPO_TARBALL = "https://github.com/Xeyaldi/userbot/tarball/main"

# MongoDB Bağlantı Protokolu
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["ht_generator_db"]
users_col = db["users"]

# Setup Bot İnstansiyası
bot = TelegramClient('ht_setup_bot', API_ID, API_HASH)

def generate_unique_name(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(
        "🛡 **HT USERBOT | Tam Avtomatlaşdırılmış İnfrastruktur**\n\n"
        "Sistemimiz hər şeyi sizin yerinizə həll edir. Artıq BotFather və ya App Name ilə vaxt itirməyə ehtiyac yoxdur.\n\n"
        "🔹 **Tam Avtomatik:** Repo qoşulması və Bot yaradılması sistem tərəfindən icra olunur.\n"
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
    async with bot.conversation(event.chat_id, timeout=300) as conv:
        try:
            # 1. Addım: Nömrə
            await conv.send_message("📝 **Addım 1:** Telefon nömrənizi daxil edin.\n_(Məsələn: +994XXXXXXXXX)_")
            phone = (await conv.get_response()).text.strip()
            
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            await client.send_code_request(phone)

            # 2. Addım: Kod
            await conv.send_message("🔐 **Addım 2:** Telegram tərəfindən gönderilən 5 rəqəmli kodu daxil edin.\n\nNümunə: `1 2 3 4 5`", parse_mode="markdown")
            otp_code = (await conv.get_response()).text.replace(" ", "")

            try:
                await client.sign_in(phone, otp_code)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **2FA (İkiadımlı təsdiq) parolu daxil edin:**")
                await client.sign_in(password=(await conv.get_response()).text.strip())
            except Exception:
                await conv.send_message("❌ **Xəta:** Məlumatlar yanlışdır.")
                return

            string_session = client.session.save()
            status_msg = await conv.send_message("⚙️ **Addım 3:** Bot yaradılır və App adı təyin edilir...")

            # --- AVTOMATİK BOTFATHER ---
            helper_token = ""
            bot_username = f"HT_{generate_unique_name(5)}_Bot"
            async with client.conversation("@BotFather") as bf_conv:
                await bf_conv.send_message("/newbot")
                await bf_conv.get_response()
                await bf_conv.send_message("HT Helper Bot")
                await bf_conv.get_response()
                await bf_conv.send_message(bot_username)
                bf_res = await bf_conv.get_response()
                if "Done!" in bf_res.text:
                    helper_token = bf_res.text.split("t.me/")[1].split("\n")[1].split(" ")[0]
                else:
                    await status_msg.edit("❌ **BotFather Limiti:** Yeni bot yaradıla bilmədi.")
                    return

            # --- HEROKU PROSESİ ---
            await status_msg.edit("🔑 **Addım 4:** Heroku API Key-inizi daxil edin:")
            h_api = (await conv.get_response()).text.strip()
            h_app_name = f"ht-user-{generate_unique_name(8)}"

            await status_msg.edit(f"⌛ **Repo Heroku-ya bağlanır və yüklənir...**\n📦 App Name: `{h_app_name}`")

            try:
                h_conn = heroku3.from_key(h_api)
                # 1. App-i Yaradırıq
                app = h_conn.create_app(name=h_app_name, region_id_or_name='eu', stack_id_or_name='heroku-22')
                
                # 2. Configləri doldururuq
                app.config().update({
                    'API_ID': str(API_ID),
                    'API_HASH': API_HASH,
                    'SESSION_STRING': string_session,
                    'BOT_TOKEN': helper_token,
                    'MONGO_URL': MONGO_URL,
                    'OWNER_ID': str(user_id),
                    'LOG_GROUP_AUTO': "True"
                })

                # 3. REPONU BAĞLAYAN ƏSAS HİSSƏ (Build)
                headers = {
                    "Authorization": f"Bearer {h_api}",
                    "Accept": "application/vnd.heroku+json; version=3",
                    "Content-Type": "application/json"
                }
                payload = {
                    "source_blob": {
                        "url": REPO_TARBALL
                    }
                }
                # Birbaşa Heroku API-nə deyirik ki, bu repodakı kodları həmin app-ə tök!
                res = requests.post(f"https://api.heroku.com/apps/{h_app_name}/builds", headers=headers, json=payload)
                
                if res.status_code in [200, 201, 202]:
                    await status_msg.edit(
                        "✅ **Quraşdırma Uğurla Tamamlandı!**\n\n"
                        f"🤖 **Bot:** @{bot_username}\n"
                        f"📦 **App:** `{h_app_name}`\n\n"
                        "🚀 **Vacib:** Kodlar repodan çəkildi. Heroku hazırda quraşdırır. 3 dəqiqə sonra `.htlive` yazaraq yoxlayın."
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
