import sqlite3, os, sys


def run(db_path):
    """Migrate art.image_url (comma-string) to art_image table. Idempotent."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        if 'art_image' in tables:
            print("Migration already applied — skipping.")
            return

        conn.execute('BEGIN')

        conn.execute('''
            CREATE TABLE art_image (
                id       INTEGER PRIMARY KEY,
                art_id   INTEGER NOT NULL,
                url      TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(art_id) REFERENCES art(id) ON DELETE CASCADE
            )
        ''')

        offset, batch = 0, 500
        while True:
            rows = conn.execute('SELECT id, image_url FROM art LIMIT ? OFFSET ?',
                                (batch, offset)).fetchall()
            if not rows:
                break
            for row in rows:
                for pos, url in enumerate(u for u in (row['image_url'] or '').split(',') if u):
                    conn.execute('INSERT INTO art_image(art_id, url, position) VALUES(?,?,?)',
                                 (row['id'], url, pos))
            offset += batch

        conn.execute('DROP VIEW IF EXISTS art_artist_view')
        conn.execute('ALTER TABLE art DROP COLUMN image_url')

        conn.execute('CREATE INDEX idx_art_artist_id    ON art(artist_id)')
        conn.execute('CREATE INDEX idx_art_tag_art_id   ON art_tag(art_id)')
        conn.execute('CREATE INDEX idx_art_tag_tag_id   ON art_tag(tag_id)')
        conn.execute('CREATE INDEX idx_art_image_art_id ON art_image(art_id)')

        conn.execute('COMMIT')
        print("Migration complete.")
    except Exception:
        conn.execute('ROLLBACK')
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    db_path = os.path.join(os.path.dirname(__file__), 'store.db')
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)
    run(db_path)
    print("Done.")
