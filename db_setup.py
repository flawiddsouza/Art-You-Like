import sqlite3, pickledb, os.path

if not os.path.isfile('store.db'):
    with sqlite3.connect('store.db') as connection:
        c = connection.cursor()
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
                image_url TEXT,
                artist_id INTEGER,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(artist_id) REFERENCES artist(id) ON UPDATE CASCADE ON DELETE CASCADE
                PRIMARY KEY(id)
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
                FOREIGN KEY(art_id) REFERENCES art(id) ON UPDATE CASCADE ON DELETE CASCADE
                FOREIGN KEY(tag_id) REFERENCES tag(id) ON UPDATE CASCADE ON DELETE CASCADE
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
        c.execute('''
            CREATE VIEW art_artist_view AS
            SELECT art.id, art.title, art.image_url, art.source, art.created_at, art.artist_id, artist.name, artist.website, art.updated_at
            FROM art
            LEFT JOIN artist
            ON art.artist_id = artist.id
        ''')

# migrate this code to the new Settings class        
# if not os.path.isfile('settings.json'):
#     pickle = pickledb.load('settings.json', False)
#     pickle.set('layout', 'grid')
#     pickle.dump()
