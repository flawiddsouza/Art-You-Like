import sqlite3, os, sys


def run(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        # Step 1: art_image schema migration
        if 'art_image' not in tables:
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
            print("Step 1 complete: art_image schema migration.")
        else:
            print("Step 1 already applied — skipping.")

        # Step 2: updated_at index
        indexes = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}
        if 'idx_art_updated_at' not in indexes:
            conn.execute('BEGIN')
            conn.execute('CREATE INDEX idx_art_updated_at ON art(updated_at DESC)')
            conn.execute('COMMIT')
            print("Step 2 complete: added idx_art_updated_at.")
        else:
            print("Step 2 already applied — skipping.")

    except Exception:
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass
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
