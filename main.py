import os
import heroku3
import asyncio
import requests
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError
from telethon.tl.functions.channels import JoinChannelRequest
from motor.motor_asyncio import AsyncIOMotorClient

# --- CONFIG VARS (Heroku-dan çəkilir) ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
GITHUB_REPO = "https://github.com/Xeyaldi/userbot"

# MongoDB Bağlantısı
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["ht_generator_db"]
users_col = db["users"]

# Botu yaradırıq (Hələ başlatmırıq)
bot = TelegramClient('ht_gen_bot', API_ID, API_HASH)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(
        "🚀 **HT USERBOT Quraşdırma Paneli**\n\n"
        "Bu bot vasitəsilə nömrənizlə giriş edib öz userbotunuzu qura bilərsiniz.\n\n"
        "📢 **Rəsmi Kanal:** @ht_bots",
        buttons=[Button.inline("✅ Qurmağa Başla", data="setup")]
    )

@bot.on(events.CallbackQuery(data="setup"))
async def setup_process(event):
    user_id = event.sender_id
    async with bot.conversation(event.chat_id) as conv:
        # 1. Nömrə istəyi
        await conv.send_message("📞 **Nömrənizi daxil edin:**\n(Məsələn: `+994501234567`)")
        phone_res = await conv.get_response()
        phone = phone_res.text
        
        # Müvəqqəti client yaradırıq
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        try:
            await client.send_code_request(phone)
        except Exception as e:
            await conv.send_message(f"❌ **Xəta:** {e}")
            return

        # 2. Kod istəyi (Sənin istədiyin formatda)
        await conv.send_message(
            "📩 **Telegram kodunu daxil edin.**\n\n"
            "⚠️ **Vacib:** Kodu rəqəmlər arası boşluqla yazın!\n"
            "Məsələn: `1 6 7 8 0` kimi.",
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
            await conv.send_message("❌ **Kod və ya parol səhvdir.** Yenidən /start yazın.")
            return

        # 3. Məlumatların saxlanılması
        string_session = client.session.save()
        
        # MongoDB-yə yazırıq
        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"phone": phone, "session": string_session}},
            upsert=True
        )

        # Kanallara avtomatik qatılma
        try:
            await client(JoinChannelRequest("@ht_bots"))
            await client(JoinChannelRequest("@sohbet_qrupus"))
        except:
            pass

        # 4. Heroku Məlumatları
        await conv.send_message("🔑 **Heroku API Key daxil edin:**")
        h_api_res = await conv.get_response()
        h_api = h_api_res.text
        
        await conv.send_message("🏷 **Userbot üçün App Name yazın:**\n(Kiçik hərflərlə, bitişik)")
        h_name_res = await conv.get_response()
        h_app_name = h_name_res.text.lower()

        await conv.send_message("⚙️ **Öz MongoDB Linkinizi daxil edin:**\n(Userbotun yaddaşı üçün)")
        u_mongo_res = await conv.get_response()
        user_mongo = u_mongo_res.text

        msg = await conv.send_message("⌛ **Userbot Heroku-ya yüklənir... Bu 2-3 dəqiqə çəkə bilər.**")

        # 5. Heroku Deploy Prosesi
        try:
            h_conn = heroku3.from_key(h_api)
            app = h_conn.create_app(name=h_app_name, region_id_or_name='eu')
            
            app.config().update({
                'API_ID': str(API_ID),
                'API_HASH': API_HASH,
                'SESSION_STRING': string_session,
                'BOT_TOKEN': BOT_TOKEN,
                'MONGO_URL': user_mongo
            })

            source_url = "https://api.github.com/repos/Xeyaldi/userbot/tarball/main"
            h_conn.create_build(app.id, source_url=source_url)

            await msg.edit(
                "✅ **HT USERBOT UĞURLA QURULDU!**\n\n"
                "🚀 Botunuz bir neçə dəqiqəyə aktiv olacaq.\n"
                "Hesabınızda `.htlive` yazaraq yoxlaya bilərsiniz.\n\n"
                "📢 @ht_bots"
            )
        except Exception as e:
            await msg.edit(f"❌ **Heroku Xətası:** {e}\n\nEhtimal ki, bu adda tətbiq artıq var və ya API Key səhvdir.")

# --- XƏTANIN HƏLLİ: ASYNCIO LOOP ---
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ Generator Bot Onlayndır!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
