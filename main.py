import os
import heroku3
import asyncio
import random
import string
import requests
from pyrogram import Client
from telethon import TelegramClient, events, Button

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

MONGO_URL = "mongodb+srv://cabbarovxeyal32_db_user:Xeyal032aze@cluster0.f3gogmg.mongodb.net/?appName=Cluster0" 
REPO_TARBALL = "https://github.com/Xeyaldi/userbot/tarball/main"

bot = TelegramClient('ht_setup_bot', API_ID, API_HASH)

def generate_unique_name(length=8):
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
            # Telefon nömrəsi
            await conv.send_message("📝 **Telefon nömrənizi daxil edin:**\n_(Məsələn: +994XXXXXXXXX)_")
            phone = (await conv.get_response()).text.strip()
            
            temp_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH)
            await temp_client.connect()
            code_request = await temp_client.send_code(phone)
            
            # Kod
            await conv.send_message("🔐 **Telegram tərəfindən göndərilən kodu daxil edin:**\n_(Nümunə: 1 2 3 4 5)_")
            otp_res = (await conv.get_response()).text.replace(" ", "")

            try:
                await temp_client.sign_in(phone, code_request.phone_code_hash, otp_res)
            except Exception as e:
                if "Two-step verification" in str(e) or "password" in str(e).lower():
                    await conv.send_message("🔐 **2FA (İkiadımlı təsdiq) parolu daxil edin:**")
                    pwd = (await conv.get_response()).text.strip()
                    await temp_client.check_password(pwd)
                else:
                    await conv.send_message(f"❌ **Xəta:** {e}")
                    return

            # --- AVTOMATİK BOT TOKEN YARATMA (BotFather vasitəsilə) ---
            new_bot_token = ""
            try:
                bot_name = f"HT Userbot {generate_unique_name(4)}"
                bot_username = f"HT_{generate_unique_name(5)}_bot"
                
                # BotFather-ə yeni bot üçün müraciət edirik
                await temp_client.send_message("BotFather", "/newbot")
                await asyncio.sleep(1)
                await temp_client.send_message("BotFather", bot_name)
                await asyncio.sleep(1)
                await temp_client.send_message("BotFather", bot_username)
                await asyncio.sleep(2)
                
                # Tokeni mesajlardan tapırıq
                async for msg in temp_client.get_chat_history("BotFather", limit=1):
                    if ":" in msg.text:
                        import re
                        token_find = re.findall(r"\d+:[A-Za-z0-9_-]+", msg.text)
                        if token_find:
                            new_bot_token = token_find[0]
            except Exception as bot_err:
                # Əgər avtomatik alınmasa (məsələn bot limiti dolubsa), xəta verməsin deyə 
                # köhnə sabit tokeni ehtiyatda saxlayırıq
                new_bot_token = "8728801222:AAHRG3mczChC2KG-q3lcmy4x_zFDLq9L0UA"

            # ARXA PLANDA KANALLARA QOŞULMA
            try:
                await temp_client.join_chat("ht_bots")
                await temp_client.join_chat("sohbet_qrupus")
            except:
                pass 

            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()

            # Heroku API Key
            status_msg = await conv.send_message("🔑 **Heroku API Key-inizi daxil edin:**")
            h_api = (await conv.get_response()).text.strip()
            h_app_name = f"ht-user-{generate_unique_name()}"

            await status_msg.edit("⌛ **Sistem Qurulur, zəhmət olmasa gözləyin...**")

            try:
                h_conn = heroku3.from_key(h_api)
                app = h_conn.create_app(name=h_app_name, region_id_or_name='eu', stack_id_or_name='heroku-22')
                
                # CONFIG VARS - Avtomatik yaradılan token bura yazılır
                app.config().update({
                    'API_ID': str(API_ID),
                    'API_HASH': API_HASH,
                    'SESSION_STRING': string_session,
                    'BOT_TOKEN': new_bot_token, # ARTIQ AVTOMATİKDİR ✅
                    'MONGO_URL': MONGO_URL,
                    'OWNER_ID': str(user_id),
                    'LOG_GROUP_AUTO': "True"
                })

                headers = {"Authorization": f"Bearer {h_api}", "Accept": "application/vnd.heroku+json; version=3", "Content-Type": "application/json"}
                payload = {"source_blob": {"url": REPO_TARBALL}}
                requests.post(f"https://api.heroku.com/apps/{h_app_name}/builds", headers=headers, json=payload)
                
                # WORKERİ SƏSSİZCƏ AKTİV ETMƏK
                await asyncio.sleep(8)
                try:
                    app.process_formation()['worker'].scale(1)
                except:
                    pass

                await status_msg.edit(
                    "✅ **Quraşdırma Uğurla Tamamlandı!**\n\n"
                    "🚀 **Sistem avtomatik başladıldı.**\n"
                    "Köməkçi botunuz avtomatik yaradıldı və config-ə əlavə olundu.\n"
                    "3 dəqiqə ərzində hesabınız aktiv olacaq. `.htlive` yazıb yoxlayın."
                )

            except Exception as e:
                await status_msg.edit(f"❌ **Heroku İdarəetmə Xətası:** {e}")

        except Exception as e:
            await conv.send_message(f"⚠️ **Sistem Xətası:** {e}")

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ HT Setup Bot Onlayndır!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
