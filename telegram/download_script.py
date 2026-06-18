import asyncio
import json
import os
import logging
from telethon import TelegramClient, events
from dotenv import load_dotenv

# =======================
# ENV
# =======================
load_dotenv()
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
chat_env = os.getenv("CHAT")

try:
    chat = int(chat_env)
except:
    chat = chat_env

# =======================
# PATHS
# =======================
IMG_DIR = "downloads/images"
GIF_DIR = "downloads/gifs"
DB_FILE = "downloaded.json"
LOG_FILE = "telegram_downloader.log"

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(GIF_DIR, exist_ok=True)

# =======================
# LOGGING
# =======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("tg")

# =======================
# LOAD DB
# =======================
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        downloaded = set(json.load(f))
else:
    downloaded = set()

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(list(downloaded), f)

# =======================
# CLIENT
# =======================
client = TelegramClient("session", api_id, api_hash)

# =======================
# DOWNLOAD WITH RETRY
# =======================
async def download_with_retry(msg, folder, retries=5):
    for attempt in range(1, retries + 1):
        try:
            path = await msg.download_media(folder)
            if path:
                log.info(f"Downloaded {path} | msg_id={msg.id}")
                return True
        except Exception as e:
            log.warning(f"Retry {attempt}/{retries} msg {msg.id}: {e}")
            await asyncio.sleep(5)

    log.error(f"FAILED msg_id={msg.id}")
    return False

# =======================
# PROCESS MESSAGE
# =======================
async def process_message(msg):
    if msg.id in downloaded:
        log.info(f"Already processed {msg.id}")
        return

    if not msg.media:
        log.info(f"Skipped {msg.id} - no media")
        return

    ok = False

    # ---------------- PHOTO ----------------
    if msg.photo:
        log.info(f"Photo detected {msg.id}")
        ok = await download_with_retry(msg, IMG_DIR)

    # ---------------- DOCUMENT ----------------
    elif msg.document:
        mime = msg.document.mime_type or ""

        # ----- IMAGE FILE -----
        if mime.startswith("image/"):
            log.info(f"Image document detected {msg.id}")
            ok = await download_with_retry(msg, IMG_DIR)

        # ----- VIDEO FILE (WhatsApp, reels, etc) -----
        elif mime.startswith("video/"):
            is_gif = False

            # detect telegram GIF (animated mp4)
            for attr in msg.document.attributes:
                if attr.__class__.__name__ == "DocumentAttributeAnimated":
                    is_gif = True
                    break

            if is_gif:
                log.info(f"GIF detected {msg.id}")
                ok = await download_with_retry(msg, GIF_DIR)
            else:
                log.info(f"Video detected {msg.id}")
                ok = await download_with_retry(msg, GIF_DIR)

        else:
            log.info(f"Unsupported document type {mime} {msg.id}")

    # ---------------- TELEGRAM VIDEO FIELD ----------------
    elif msg.video:
        log.info(f"Telegram video detected {msg.id}")
        ok = await download_with_retry(msg, GIF_DIR)

    # ---------------- RESULT ----------------
    if ok:
        downloaded.add(msg.id)
        save_db()
        log.info(f"Saved msg_id {msg.id}")
    else:
        log.info(f"Media not matching filters {msg}")


# =======================
# DOWNLOAD OLD HISTORY
# =======================
async def download_history():
    log.info("Checking old messages...")

    async for msg in client.iter_messages(chat, reverse=True):
        await process_message(msg)

    log.info("Old message scan complete")

# =======================
# NEW MESSAGE HANDLER
# =======================
@client.on(events.NewMessage(chats=chat, incoming=True, outgoing=True))
async def handler(event):
    print("EVENT FIRED:", event.message.id, "outgoing:", event.out)
    await process_message(event.message)

# =======================
# MAIN LOOP WITH AUTO RESTART
# =======================
async def run_forever():
    while True:
        try:
            log.info("Starting client...")
            await client.start()

            # download old messages first
            await download_history()

            log.info("Now monitoring new messages 24/7...")
            await client.run_until_disconnected()

        except Exception as e:
            log.error(f"Crash: {e}")
            log.info("Restarting in 10 seconds...")
            await asyncio.sleep(10)

asyncio.run(run_forever())
