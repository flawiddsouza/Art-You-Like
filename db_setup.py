import sqlite3, os.path


def create_schema(conn):
    c = conn.cursor()
    c.execute('''
        CREATE TABLE artist(
            id INTEGER,
            name TEXT,
            website TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(id)
        )
    ''')
    c.execute('''
        CREATE TABLE art(
            id INTEGER,
            title TEXT,
            artist_id INTEGER,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(artist_id) REFERENCES artist(id) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY(id)
        )
    ''')
    c.execute('''
        CREATE TABLE art_image(
            id INTEGER PRIMARY KEY,
            art_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(art_id) REFERENCES art(id) ON DELETE CASCADE
        )
    ''')
    c.execute('''
        CREATE TABLE tag(
            id INTEGER,
            name TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(id)
        )
    ''')
    c.execute('''
        CREATE TABLE art_tag(
            id INTEGER,
            art_id INTEGER,
            tag_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(art_id) REFERENCES art(id) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY(tag_id) REFERENCES tag(id) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY(id)
        )
    ''')
    c.execute('''
        CREATE VIEW art_tag_view AS
        SELECT art_tag.id, art_tag.art_id, art_tag.tag_id, tag.name
        FROM art_tag
        LEFT JOIN tag
        ON art_tag.tag_id = tag.id
    ''')
    c.execute('CREATE INDEX idx_art_artist_id    ON art(artist_id)')
    c.execute('CREATE INDEX idx_art_tag_art_id   ON art_tag(art_id)')
    c.execute('CREATE INDEX idx_art_tag_tag_id   ON art_tag(tag_id)')
    c.execute('CREATE INDEX idx_art_image_art_id ON art_image(art_id)')


if not os.path.isfile('store.db'):
    with sqlite3.connect('store.db') as connection:
        create_schema(connection)

# migrate this code to the new Settings class        
# if not os.path.isfile('settings.json'):
#     pickle = pickledb.load('settings.json', False)
#     pickle.set('layout', 'grid')
#     pickle.dump()
