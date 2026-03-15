import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired, PhoneNumberInvalid
)
from telethon import TelegramClient, functions
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

# Heroku Config Vars
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("HTSessionBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_data = {}

START_TEXT = """
<b>⚡️ HT Session Bot-a Xoş Gəlmisiniz</b>

Bu bot vasitəsilə ən müasir kitabxanalar üçün təhlükəsiz <b>String Session</b> əldə edə bilərsiniz.

<b>🛠 Texniki Dəstək:</b>
• <code>Pyrogram V2</code> (Ən son)
• <code>Telethon</code> (Stabil)

⚠️ <b>Təhlükəsizlik:</b> Sessiya kodunuz heç bir yerdə saxlanılmır və birbaşa sizin <b>'Saved Messages'</b> bölmənizə göndərilir.

<i>Zəhmət olmasa aşağıdan seçim edin:</i>
"""

@app.on_message(filters.command("start") & filters.private)
async def start(bot, message):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 Pyrogram", callback_data="choice_pyro"),
            InlineKeyboardButton("💎 Telethon", callback_data="choice_tele")
        ],
        [
            InlineKeyboardButton("📢 Rəsmi Kanal", url="https://t.me/ht_bots")
        ]
    ])
    await message.reply_text(START_TEXT, reply_markup=buttons)

@app.on_callback_query(filters.regex("choice_"))
async def choice_handler(bot, query):
    method = query.data.split("_")[1]
    user_data[query.from_user.id] = {"method": method, "step": "API_ID"}
    await query.message.edit_text(
        f"✅ <b>{method.upper()} seçildi.</b>\n\nLütfən <code>API ID</code> daxil edin:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="cancel")]])
    )

@app.on_callback_query(filters.regex("cancel"))
async def cancel_handler(bot, query):
    user_id = query.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    await query.message.edit_text("❌ Əməliyyat ləğv edildi. Yenidən başlamaq üçün /start yazın.")

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
        await message.reply("İndi isə <code>API HASH</code> daxil edin:")

    elif step == "API_HASH":
        data["api_hash"] = message.text
        data["step"] = "PHONE"
        await message.reply("📲 <b>Telefon Nömrənizi</b> daxil edin:\n(Nümunə: <code>+994XXXXXXXXX</code>)")

    elif step == "PHONE":
        data["phone"] = message.text.replace(" ", "")
        await message.reply("⏳ <b>Doğrulama kodu göndərilir...</b>")
        
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
            await message.reply("📩 Telegram tətbiqinə gələn <b>5 rəqəmli kodu</b> göndərin:")
        
        except Exception as e:
            await message.reply(f"❌ <b>Xəta:</b> <code>{str(e)}</code>")
            del user_data[user_id]

    elif step == "OTP":
        client = data["client"]
        otp = message.text.replace(" ", "")
        
        try:
            if data["method"] == "pyro":
                await client.sign_in(data["phone"], data["code_hash"], otp)
                # Avto Kanal Qoşulma
                try: await client.join_chat("ht_bots")
                except: pass
                
                session_str = await client.export_session_string()
                await client.send_message("me", f"🚀 <b>HT Session Bot | Pyrogram</b>\n\n<code>{session_str}</code>\n\n👤 @ht_bots")
            else:
                await client.sign_in(data["phone"], otp, phone_code_hash=data["code_hash"])
                # Avto Kanal Qoşulma
                try: await client(functions.channels.JoinChannelRequest(channel='ht_bots'))
                except: pass
                
                session_str = client.session.save()
                await client.send_message("me", f"🚀 <b>HT Session Bot | Telethon</b>\n\n<code>{session_str}</code>\n\n👤 @ht_bots")

            await message.reply("✨ <b>Uğurlu!</b>\n\nSessiya kodunuz <b>Saved Messages</b> bölməsinə göndərildi. Təhlükəsizliyiniz üçün bu çatdakı mesajları silə bilərsiniz.")
            await client.disconnect()
            del user_data[user_id]
            
        except (SessionPasswordNeeded, SessionPasswordNeededError):
            data["step"] = "PASSWORD"
            await message.reply("🔐 Hesabda <b>İki Mərhələli Doğrulama</b> aktivdir. Lütfən parolu daxil edin:")
        except Exception as e:
            await message.reply(f"❌ <b>Xəta:</b> {str(e)}")

    elif step == "PASSWORD":
        client = data["client"]
        try:
            if data["method"] == "pyro":
                await client.check_password(message.text)
                try: await client.join_chat("ht_bots")
                except: pass
                session_str = await client.export_session_string()
                await client.send_message("me", f"🚀 <b>HT Session Bot | Pyrogram (2FA)</b>\n\n<code>{session_str}</code>")
            else:
                await client.sign_in(password=message.text)
                try: await client(functions.channels.JoinChannelRequest(channel='ht_bots'))
                except: pass
                session_str = client.session.save()
                await client.send_message("me", f"🚀 <b>HT Session Bot | Telethon (2FA)</b>\n\n<code>{session_str}</code>")
                
            await message.reply("✨ <b>Uğurlu!</b> Sessiya <b>Saved Messages</b> bölməsinə atıldı.")
            await client.disconnect()
            del user_data[user_id]
        except Exception as e:
            await message.reply(f"❌ <b>Parol səhvdir:</b> {str(e)}")

async def main():
    async with app:
        await asyncio.Event().wait()

if __name__ == "__main__":
    app.run()
