import os
import heroku3
import asyncio
import random
import string
import requests
import re
from pyrogram import Client
from telethon import TelegramClient, events, Button

# --- CONFIGURATION (Sənin orijinalın) ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = 8371395083 # Sənin ID-n (YENİ)

MONGO_URL = "mongodb+srv://cabbarovxeyal32_db_user:Xeyal032aze@cluster0.f3gogmg.mongodb.net/?appName=Cluster0" 
REPO_TARBALL = "https://github.com/Xeyaldi/userbot/tarball/main"

bot = TelegramClient('ht_setup_bot', API_ID, API_HASH)
installed_users = set() # Statistika üçün (YENİ)

def generate_unique_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# --- START MESAJI (Orijinal mətni saxlanıldı + Yeni butonlar) ---
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(
        "🛡 **HT USERBOT | Rəsmi Quraşdırma İnfrastrukturu**\n\n"
        "Sistemimiz istifadəçi təhlükəsizliyini və performansını ön planda tutan avtomatlaşdırılmış quraşdırma xidmətini təqdim edir.\n\n"
        "🔹 **Təhlükəsizlik:** Bütün məlumatlar şifrələnmiş kanallar vasitəsilə ötürülür.\n"
        "🔹 **Sürət:** Bulud texnologiyası sayəsində quraşdırma cəmi 120 saniyə çəkir.\n"
        "🔹 **Dəstək:** Tam professional interfeys və 7/24 rəsmi infrastruktur.\n\n"
        "Davam etməklə istifadə qaydalarını və təhlükəsizlik protokolunu qəbul etmiş olursunuz.",
        buttons=[
            [Button.inline("💎 Quraşdırmanı Başlat", data="setup")],
            [Button.url("📢 Yeniliklər", "https://t.me/ht_bots")], # YENİ
            [Button.url("👥 Dəstək Qrupu", "https://t.me/sohbet_qrupus")], # YENİ
            [Button.url("🌐 Rəsmi Kanal", "https://t.me/ht_bots")]
        ]
    )

# --- ADMIN STATS (YENİ FUNKSİYA) ---
@bot.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if event.sender_id == OWNER_ID:
        await event.respond(f"📊 **Bot Statistikası:**\n\n✅ Ümumi quraşdırma: {len(installed_users)}\n👤 İstifadəçi ID-ləri: `{list(installed_users)}`")

@bot.on(events.CallbackQuery(data="setup"))
async def setup_process(event):
    user_id = event.sender_id
    async with bot.conversation(event.chat_id, timeout=600) as conv:
        try:
            # 1. HEROKU API (Orijinal yoxlanış)
            await conv.send_message("🔑 **Lütfən Heroku API Key-inizi daxil edin:**")
            h_api = (await conv.get_response()).text.strip()
            
            # API Headers (Worker üçün lazım olacaq)
            h_headers = {
                "Authorization": f"Bearer {h_api}",
                "Accept": "application/vnd.heroku+json; version=3",
                "Content-Type": "application/json"
            }

            try:
                h_conn = heroku3.from_key(h_api)
                h_conn.apps() 
            except:
                return await conv.send_message("❌ **Xəta:** Heroku API Key yanlışdır.")

            # 2. TELEFON NÖMRƏSİ
            await conv.send_message("📝 **Telefon nömrənizi daxil edin:**\n_(Məsələn: +994XXXXXXXXX)_")
            phone = (await conv.get_response()).text.strip()
            
            temp_client = Client("ht_session", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            code_request = await temp_client.send_code(phone)
            
            await conv.send_message("🔐 **Telegram tərəfindən göndərilən kodu daxil edin:**")
            otp_res = (await conv.get_response()).text.replace(" ", "")

            try:
                await temp_client.sign_in(phone, code_request.phone_code_hash, otp_res)
            except Exception as e:
                if "Two-step verification" in str(e) or "password" in str(e).lower():
                    await conv.send_message("🔐 **2FA (İkiadımlı təsdiq) parolu daxil edin:**")
                    pwd = (await conv.get_response()).text.strip()
                    await temp_client.check_password(pwd)
                else: return await conv.send_message(f"❌ **Xəta:** {e}")

            status_msg = await conv.send_message("⌛ **Sistem Qurulur, zəhmət olmasa gözləyin...**")

            # --- BOTFATHER VƏ INLINE (Tamamilə orijinal, toxunulmadı) ---
            new_bot_token = ""
            try:
                bot_name = f"HT Userbot {generate_unique_name(4)}"
                bot_username = f"HT_{generate_unique_name(5)}_bot"
                await temp_client.send_message("BotFather", "/newbot")
                await asyncio.sleep(2); await temp_client.send_message("BotFather", bot_name)
                await asyncio.sleep(2); await temp_client.send_message("BotFather", bot_username)
                await asyncio.sleep(3)
                async for msg in temp_client.get_chat_history("BotFather", limit=1):
                    token_find = re.findall(r"\d+:[A-Za-z0-9_-]+", msg.text)
                    if token_find:
                        new_bot_token = token_find[0]
                        await temp_client.send_message("BotFather", "/setinline")
                        await asyncio.sleep(1); await temp_client.send_message("BotFather", f"@{bot_username}")
                        await asyncio.sleep(1); await temp_client.send_message("BotFather", "HT Inline")
            except: new_bot_token = BOT_TOKEN

            # KANALLARA QOŞULMA (Orijinal)
            try:
                await temp_client.join_chat("ht_bots")
                await temp_client.join_chat("sohbet_qrupus")
            except: pass

            string_session = await temp_client.export_session_string()
            await temp_client.disconnect()

            # --- HEROKU DEPLOY (Orijinal) ---
            h_app_name = f"ht-user-{generate_unique_name()}"
            try:
                app = h_conn.create_app(name=h_app_name, region_id_or_name='eu', stack_id_or_name='heroku-22')
                app.config().update({
                    'API_ID': str(API_ID), 'API_HASH': API_HASH,
                    'SESSION_STRING': string_session, 'BOT_TOKEN': new_bot_token,
                    'MONGO_URL': MONGO_URL, 'OWNER_ID': str(user_id), 'LOG_GROUP_AUTO': "True"
                })

                requests.post(f"https://api.heroku.com/apps/{h_app_name}/builds", headers=h_headers, json={"source_blob": {"url": REPO_TARBALL}})
                
                # --- WORKER PROBLEMİNİN MÜASİR HƏLLİ (YENİ) ---
                await status_msg.edit("🚀 **Build başladı, worker 75 saniyə sonra avtomatik qoşulacaq...**")
                await asyncio.sleep(75) 
                
                # Ən müasir API PATCH sorğusu ilə worker aktivləşdirmə
                requests.patch(f"https://api.heroku.com/apps/{h_app_name}/formation", headers=h_headers, json={
                    "updates": [{"type": "worker", "quantity": 1}]
                })

                # --- STATİSTİKA VƏ QRUP BİLDİRİŞİ (YENİ FUNKSİYA) ---
                installed_users.add(user_id)
                try:
                    await bot.send_message("@sohbet_qrupus", f"🎉 **Yeni Quraşdırma!**\n👤 **İstifadəçi:** [{event.sender.first_name}](tg://user?id={user_id})\n🚀 Userbot avtomatik aktiv edildi!")
                except: pass

                await status_msg.edit("✅ **Quraşdırma Uğurla Tamamlandı!**\n\n🚀 Sistem başladı.")

            except Exception as e:
                await status_msg.edit(f"❌ **Heroku Xətası:** {e}")

        except Exception as e:
            await conv.send_message(f"⚠️ **Sistem Xətası:** {e}")

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
