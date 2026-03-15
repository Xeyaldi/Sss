import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

# Heroku Config Vars
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("LunaSessionBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_data = {}

START_TEXT = """
<b>🌙 HT Sessiya Botu</b>

Bu bot vasitəsilə aldığınız sessiya kodları təhlükəsizlik üçün birbaşa sizin <b>"Yadda Saxlanılan Mesajlar" (Saved Messages)</b> bölmənizə göndərilir.

<i>Zəhmət olmasa kitabxananı seçin:</i>
"""

@app.on_message(filters.command("start") & filters.private)
async def start(bot, message):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔹 Pyrogram", callback_data="choice_pyro"),
            InlineKeyboardButton("🔷 Telethon", callback_data="choice_tele")
        ]
    ])
    await message.reply_text(START_TEXT, reply_markup=buttons)

@app.on_callback_query(filters.regex("choice_"))
async def choice_handler(bot, query):
    method = query.data.split("_")[1]
    user_data[query.from_user.id] = {"method": method, "step": "API_ID"}
    await query.message.edit_text(f"✅ <b>{method.upper()}</b> seçildi.\n\nLütfən <b>API ID</b> daxil edin:")

@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def logic_handler(bot, message):
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    data = user_data[user_id]
    step = data.get("step")

    if step == "API_ID":
        data["api_id"] = message.text
        data["step"] = "API_HASH"
        await message.reply("İndi isə <b>API HASH</b> daxil edin:")

    elif step == "API_HASH":
        data["api_hash"] = message.text
        data["step"] = "PHONE"
        await message.reply("<b>Telefon Nömrənizi</b> göndərin (Məs: +994501234567):")

    elif step == "PHONE":
        data["phone"] = message.text
        await message.reply("⏳ Kod göndərilir...")
        
        try:
            if data["method"] == "pyro":
                client = Client(":memory:", api_id=data["api_id"], api_hash=data["api_hash"])
            else:
                client = TelegramClient(StringSession(), data["api_id"], data["api_hash"])
            
            await client.connect()
            
            if data["method"] == "pyro":
                code_hash = await client.send_code(data["phone"])
                data["code_hash"] = code_hash.phone_code_hash
            else:
                code_hash = await client.send_code_request(data["phone"])
                data["code_hash"] = code_hash.phone_code_hash
            
            data["client"] = client
            data["step"] = "OTP"
            await message.reply("📩 Telegram-dan gələn <b>5 rəqəmli kodu</b> daxil edin:")
        
        except Exception as e:
            await message.reply(f"❌ Xəta: {str(e)}")
            del user_data[user_id]

    elif step == "OTP":
        client = data["client"]
        otp = message.text.replace(" ", "")
        
        try:
            if data["method"] == "pyro":
                await client.sign_in(data["phone"], data["code_hash"], otp)
                session_str = await client.export_session_string()
                # Saved Messages-ə göndər
                await client.send_message("me", f"🚀 **Luna Music - Pyrogram Sessiyanız:**\n\n`{session_str}`")
            else:
                await client.sign_in(data["phone"], otp, phone_code_hash=data["code_hash"])
                session_str = client.session.save()
                # Saved Messages-ə göndər
                await client.send_message("me", f"🚀 **Luna Music - Telethon Sessiyanız:**\n\n`{session_str}`")

            await message.reply("✅ <b>Uğurlu!</b>\n\nSessiya kodunuz təhlükəsizlik üçün <b>Yadda Saxlanılan Mesajlar (Saved Messages)</b> bölməsinə göndərildi. Lütfən oradan yoxlayın.")
            await client.disconnect()
            del user_data[user_id]
            
        except (SessionPasswordNeeded, SessionPasswordNeededError):
            data["step"] = "PASSWORD"
            await message.reply("🔐 Hesabınızda 2FA (İki mərhələli doğrulama) var. Parolu daxil edin:")
        except Exception as e:
            await message.reply(f"❌ Xəta: {str(e)}")

    elif step == "PASSWORD":
        client = data["client"]
        try:
            if data["method"] == "pyro":
                await client.check_password(message.text)
                session_str = await client.export_session_string()
                await client.send_message("me", f"🚀 **Luna Music - Pyrogram Sessiyanız (2FA):**\n\n`{session_str}`")
            else:
                await client.sign_in(password=message.text)
                session_str = client.session.save()
                await client.send_message("me", f"🚀 **Luna Music - Telethon Sessiyanız (2FA):**\n\n`{session_str}`")
                
            await message.reply("✅ <b>Uğurlu!</b>\n\nSessiya kodunuz <b>Saved Messages</b> bölməsinə göndərildi.")
            await client.disconnect()
            del user_data[user_id]
        except Exception as e:
            await message.reply(f"❌ Parol səhvdir: {str(e)}")

app.run()
