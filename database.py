import sqlite3
from datetime import date

DB_PATH = 'news.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            description TEXT,
            source TEXT,
            published_date TEXT,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_published_date ON articles(published_date)
    ''')
    conn.commit()
    conn.close()

def save_articles(articles):
    conn = get_db()
    saved = 0
    for a in articles:
        try:
            conn.execute(
                'INSERT OR IGNORE INTO articles (title, link, description, source, published_date) VALUES (?, ?, ?, ?, ?)',
                (a['title'], a['link'], a['description'], a['source'], a['published_date'])
            )
            if conn.execute('SELECT changes()').fetchone()[0] > 0:
                saved += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return saved

def get_articles_by_date(target_date):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM articles WHERE published_date = ? ORDER BY fetched_at DESC',
        (target_date,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_available_dates():
    conn = get_db()
    rows = conn.execute(
        'SELECT DISTINCT published_date FROM articles ORDER BY published_date DESC LIMIT 30'
    ).fetchall()
    conn.close()
    return [r['published_date'] for r in rows]

def get_sources_by_date(target_date):
    conn = get_db()
    rows = conn.execute(
        'SELECT DISTINCT source FROM articles WHERE published_date = ? ORDER BY source',
        (target_date,)
    ).fetchall()
    conn.close()
    return [r['source'] for r in rows]

def get_articles_by_date_and_source(target_date, source):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM articles WHERE published_date = ? AND source = ? ORDER BY fetched_at DESC',
        (target_date, source)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_articles(keyword, limit=50):
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM articles WHERE title LIKE ? OR description LIKE ? ORDER BY published_date DESC, fetched_at DESC LIMIT ?',
        (f'%{keyword}%', f'%{keyword}%', limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_total_count():
    conn = get_db()
    row = conn.execute('SELECT COUNT(*) as cnt FROM articles').fetchone()
    conn.close()
    return row['cnt']
