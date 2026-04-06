import pytest, json, sqlite3
from unittest.mock import patch


def test_get_all_art_shape(client):
    resp = client.get('/art/all')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 1
    art = data[0]
    assert art['id'] == 1
    assert art['title'] == 'Test Art'
    assert art['artist_name'] == 'Test Artist'
    assert art['image_url'] == ['img1.jpg', 'img2.jpg']
    assert len(art['tags']) == 2
    tag_names = {t['tag_name'] for t in art['tags']}
    assert tag_names == {'nature', 'portrait'}


def test_get_all_art_count(client):
    resp = client.get('/art/all/count')
    assert json.loads(resp.data) == 1


def test_get_all_art_respects_count(client):
    resp = client.get('/art/all?count=0')
    assert json.loads(resp.data) == []


def test_get_art_page(client):
    resp = client.get('/art/1')
    assert resp.status_code == 200
    assert b'Test Art' in resp.data


def test_get_art_invalid_id_redirects(client):
    assert client.get('/art/abc').status_code == 302


def test_get_art_missing_id_redirects(client):
    assert client.get('/art/999').status_code == 302


def test_index_loads(client):
    assert client.get('/').status_code == 200


def test_search_json_finds_by_title(client):
    resp = client.get('/search_json?q=Test')
    data = json.loads(resp.data)
    assert len(data) == 1
    assert data[0]['title'] == 'Test Art'


def test_search_json_empty_query(client):
    assert json.loads(client.get('/search_json').data) == []


def test_search_json_count(client):
    assert json.loads(client.get('/search_json/count?q=Test').data) == 1


def test_search_page_loads(client):
    assert client.get('/search?q=Test').status_code == 200


def test_tag_manager_loads(client):
    assert client.get('/tag-manager').status_code == 200


def test_artist_manager_loads(client):
    assert client.get('/artist-manager').status_code == 200


def test_settings_loads(client):
    assert client.get('/settings').status_code == 200


def test_delete_art_removes_record(client):
    resp = client.post('/art/delete', data={'id': '1'})
    assert resp.status_code in (200, 302)
    assert json.loads(client.get('/art/all').data) == []


def test_delete_art_image_removes_row(client, test_db_path):
    client.post('/art/image/delete', data={'id': '1', 'image_url': 'img1.jpg'})
    with sqlite3.connect(test_db_path) as conn:
        rows = conn.execute('SELECT url FROM art_image WHERE art_id=1').fetchall()
    assert len(rows) == 1 and rows[0][0] == 'img2.jpg'


def test_add_art_creates_record(client):
    with patch('helpers.download', return_value='downloaded.jpg'):
        resp = client.post('/art/add', data={
            'title': 'New Art',
            'local-image': 'false',
            'image-from-url': 'http://example.com/img.jpg',
            'existing-artist': 'true',
            'artist-id': '1',
            'source': 'http://example.com',
        })
    assert resp.status_code == 302
    data = json.loads(client.get('/art/all').data)
    assert len(data) == 2
    titles = {a['title'] for a in data}
    assert 'New Art' in titles


def test_artist_manager_art_count_correct(client, test_db_path):
    """art_count must reflect actual art rows per artist, including zero."""
    with sqlite3.connect(test_db_path) as conn:
        conn.execute("INSERT INTO artist(id,name,website) VALUES(2,'Artist B','http://b.com')")
        conn.execute("INSERT INTO art(id,title,artist_id,source) VALUES(2,'Art 2',1,'http://s.com')")
        conn.commit()
    resp = client.get('/artist-manager')
    assert resp.status_code == 200
    assert b'>2<' in resp.data   # artist 1 now has 2 arts
    assert b'>0<' in resp.data   # artist 2 has 0 arts


def test_tag_manager_art_count_correct(client, test_db_path):
    """art_count must reflect actual art_tag rows per tag, including zero."""
    with sqlite3.connect(test_db_path) as conn:
        conn.execute("INSERT INTO tag(id,name) VALUES(3,'landscape')")
        conn.commit()
    resp = client.get('/tag-manager')
    assert resp.status_code == 200
    assert b'>0<' in resp.data   # tag 3 has no art
    assert b'>1<' in resp.data   # tags 1 and 2 each have 1 art from seed


def test_get_all_art_includes_image_dims(client):
    data = json.loads(client.get('/art/all').data)
    dims = data[0]['image_dims']
    assert dims['img1.jpg'] == {'width': 1920, 'height': 1080}
    assert dims['img2.jpg'] == {'width': 800,  'height': 600}


def test_add_art_stores_image_dims(client, test_db_path):
    with patch('helpers.download', return_value='new_img.jpg'), \
         patch('helpers.get_image_dims', return_value=(800, 600)):
        client.post('/art/add', data={
            'title': 'Dims Art',
            'local-image': 'false',
            'image-from-url': 'http://example.com/img.jpg',
            'existing-artist': 'true',
            'artist-id': '1',
            'source': 'http://example.com',
        })
    with sqlite3.connect(test_db_path) as conn:
        row = conn.execute(
            'SELECT width, height FROM art_image WHERE url=?', ('new_img.jpg',)
        ).fetchone()
    assert row == (800, 600)


def test_index_page_uses_correct_viewbox(client):
    resp = client.get('/')
    # img1.jpg seeded with width=1920, height=1080
    assert b"viewBox%3D'0 0 1920 1080'" in resp.data
