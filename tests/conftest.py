import pytest
import sqlite3
import os
import json
import tempfile

os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest')

from main import app as flask_app
from db_setup import create_schema


def seed_test_db(db_path):
    with sqlite3.connect(db_path) as conn:
        create_schema(conn)
        conn.execute("INSERT INTO artist(id,name,website) VALUES(1,'Test Artist','http://example.com')")
        conn.execute("INSERT INTO art(id,title,artist_id,source) VALUES(1,'Test Art',1,'http://source.com')")
        conn.execute("INSERT INTO art_image(art_id,url,position) VALUES(1,'img1.jpg',0)")
        conn.execute("INSERT INTO art_image(art_id,url,position) VALUES(1,'img2.jpg',1)")
        conn.execute("INSERT INTO tag(id,name) VALUES(1,'nature')")
        conn.execute("INSERT INTO tag(id,name) VALUES(2,'portrait')")
        conn.execute("INSERT INTO art_tag(art_id,tag_id) VALUES(1,1)")
        conn.execute("INSERT INTO art_tag(art_id,tag_id) VALUES(1,2)")
        conn.commit()


@pytest.fixture
def test_db_path():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    seed_test_db(path)
    yield path
    try:
        os.unlink(path)
    except PermissionError:
        pass  # Windows: SQLite may hold a brief lock after close


@pytest.fixture
def client(test_db_path, tmp_path):
    settings_path = str(tmp_path / 'settings.json')
    with open(settings_path, 'w') as f:
        json.dump({'layout': 'grid'}, f)

    flask_app.config['TESTING'] = True
    flask_app.database = test_db_path
    flask_app.settings_database = settings_path
    with flask_app.test_client() as c:
        yield c
