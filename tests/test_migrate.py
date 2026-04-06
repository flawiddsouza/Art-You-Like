import sqlite3, os, tempfile, pytest

OLD_SCHEMA_SQL = '''
    CREATE TABLE artist (id INTEGER PRIMARY KEY, name TEXT, website TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE art (id INTEGER PRIMARY KEY, title TEXT, image_url TEXT,
        artist_id INTEGER, source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(artist_id) REFERENCES artist(id));
    CREATE TABLE tag (id INTEGER PRIMARY KEY, name TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE art_tag (id INTEGER PRIMARY KEY, art_id INTEGER, tag_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(art_id) REFERENCES art(id),
        FOREIGN KEY(tag_id) REFERENCES tag(id));
    CREATE VIEW art_tag_view AS
        SELECT art_tag.id, art_tag.art_id, art_tag.tag_id, tag.name
        FROM art_tag LEFT JOIN tag ON art_tag.tag_id = tag.id;
    CREATE VIEW art_artist_view AS
        SELECT art.id, art.title, art.image_url, art.source, art.created_at,
               art.artist_id, artist.name, artist.website, art.updated_at
        FROM art LEFT JOIN artist ON art.artist_id = artist.id;
'''


@pytest.fixture
def old_db():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    with sqlite3.connect(path) as conn:
        conn.executescript(OLD_SCHEMA_SQL)
        conn.execute("INSERT INTO artist(id,name,website) VALUES(1,'A','http://a.com')")
        conn.execute("INSERT INTO art(id,title,image_url,artist_id,source) VALUES(1,'Art1','a.jpg,b.jpg',1,'http://s.com')")
        conn.execute("INSERT INTO art(id,title,image_url,artist_id,source) VALUES(2,'Art2','c.jpg',1,'http://s2.com')")
        conn.execute("INSERT INTO art(id,title,image_url,artist_id,source) VALUES(3,'Art3','',1,'http://s3.com')")
        conn.commit()
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass  # Windows: SQLite may hold a brief lock after close


def run(db_path):
    import migrate
    migrate.run(db_path)


def test_creates_art_image_table(old_db):
    run(old_db)
    with sqlite3.connect(old_db) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert 'art_image' in tables


def test_removes_image_url_column(old_db):
    run(old_db)
    with sqlite3.connect(old_db) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(art)").fetchall()]
    assert 'image_url' not in cols


def test_preserves_multi_image_order(old_db):
    run(old_db)
    with sqlite3.connect(old_db) as conn:
        rows = conn.execute("SELECT url,position FROM art_image WHERE art_id=1 ORDER BY position").fetchall()
    assert rows == [('a.jpg', 0), ('b.jpg', 1)]


def test_preserves_single_image(old_db):
    run(old_db)
    with sqlite3.connect(old_db) as conn:
        rows = conn.execute("SELECT url,position FROM art_image WHERE art_id=2").fetchall()
    assert rows == [('c.jpg', 0)]


def test_skips_empty_image_url(old_db):
    run(old_db)
    with sqlite3.connect(old_db) as conn:
        rows = conn.execute("SELECT url FROM art_image WHERE art_id=3").fetchall()
    assert rows == []


def test_is_idempotent(old_db):
    run(old_db)
    run(old_db)  # second run must not raise or duplicate data
    with sqlite3.connect(old_db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM art_image").fetchone()[0]
    assert count == 3


def test_creates_indexes(old_db):
    run(old_db)
    with sqlite3.connect(old_db) as conn:
        indexes = [r[1] for r in conn.execute("SELECT * FROM sqlite_master WHERE type='index'").fetchall()]
    for idx in ['idx_art_artist_id', 'idx_art_tag_art_id', 'idx_art_tag_tag_id', 'idx_art_image_art_id']:
        assert idx in indexes


def test_drops_art_artist_view(old_db):
    run(old_db)
    with sqlite3.connect(old_db) as conn:
        views = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()]
    assert 'art_artist_view' not in views


# --- Step 2: idx_art_updated_at ---

@pytest.fixture
def post_step1_db():
    """DB already migrated through step 1 but missing idx_art_updated_at (simulates pre-fix state)."""
    from db_setup import create_schema
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    with sqlite3.connect(path) as conn:
        create_schema(conn)
        conn.execute('DROP INDEX IF EXISTS idx_art_updated_at')
        conn.commit()
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _indexes(path):
    with sqlite3.connect(path) as conn:
        return {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()}


def test_step2_creates_updated_at_index_from_old_schema(old_db):
    """Running migrate on old schema applies both steps including the index."""
    run(old_db)
    assert 'idx_art_updated_at' in _indexes(old_db)


def test_step2_creates_updated_at_index_skipping_step1(post_step1_db):
    """Running migrate on a post-step-1 DB skips step 1 and applies step 2."""
    assert 'idx_art_updated_at' not in _indexes(post_step1_db)
    run(post_step1_db)
    assert 'idx_art_updated_at' in _indexes(post_step1_db)


def test_step2_is_idempotent(post_step1_db):
    run(post_step1_db)
    run(post_step1_db)  # second run must not raise
    assert 'idx_art_updated_at' in _indexes(post_step1_db)


def test_create_schema_includes_updated_at_index(tmp_path):
    """Fresh installs via db_setup.py include idx_art_updated_at."""
    from db_setup import create_schema
    path = str(tmp_path / 'fresh.db')
    with sqlite3.connect(path) as conn:
        create_schema(conn)
    assert 'idx_art_updated_at' in _indexes(path)
