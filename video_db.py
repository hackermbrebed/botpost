import sqlite3

def init_db():
    conn = sqlite3.connect('video_links.db')
    cursor = conn.cursor()
    # Tabel untuk menyimpan video
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT NOT NULL,
            caption TEXT
        )
    ''')
    # Tabel untuk menyimpan ID grup yang dikelola bot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS managed_groups (
            chat_id INTEGER PRIMARY KEY
        )
    ''')
    # Tabel baru untuk menyimpan ID channel Force Subscribe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_video(file_id, caption=None):
    conn = sqlite3.connect('video_links.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO videos (file_id, caption) VALUES (?, ?)", (file_id, caption))
    conn.commit()
    conn.close()

def get_all_videos():
    conn = sqlite3.connect('video_links.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, caption FROM videos ORDER BY id DESC")
    videos = cursor.fetchall()
    conn.close()
    return videos

def add_managed_group(chat_id):
    conn = sqlite3.connect('video_links.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO managed_groups (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError: # Jika chat_id sudah ada
        return False
    finally:
        conn.close()

def remove_managed_group(chat_id):
    conn = sqlite3.connect('video_links.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM managed_groups WHERE chat_id = ?", (chat_id,))
    conn.commit()
    return cursor.rowcount > 0 # Mengembalikan True jika ada baris yang dihapus

def is_group_managed(chat_id):
    conn = sqlite3.connect('video_links.db')
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM managed_groups WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_managed_groups():
    conn = sqlite3.connect('video_links.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM managed_groups")
    groups = [row[0] for row in cursor.fetchall()]
    conn.close()
    return groups

# --- Fungsi baru untuk konfigurasi ---
def set_config(key, value):
    conn = sqlite3.connect('video_links.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_config(key):
    conn = sqlite3.connect('video_links.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Panggil ini saat bot dimulai untuk memastikan tabel dibuat
init_db()
