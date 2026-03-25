from flask import Flask, jsonify, render_template, request, redirect, g, flash
import helpers, sqlite3, json, os, re, scrapers
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/images/')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
app.database = os.path.join(os.path.dirname(__file__), 'store.db')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.settings_database = os.path.join(os.path.dirname(__file__), 'settings.json')

@app.route('/')
def index():
    g.db   = connect_db()
    art    = get_all_art_data(g.db, count=51)
    g.db.close()
    return render_template('index.html', art=art, layout=load_settings().get('layout'))

def get_all_art_data(db, sort_by=None, count=51, offset=0):
    order = 'ORDER BY a.title DESC' if sort_by == 'title' else 'ORDER BY a.updated_at DESC'
    rows = db.execute(f'{_BASE_ART_SELECT} {order} LIMIT ? OFFSET ?',
                      [count, offset]).fetchall()
    art = [_row_to_art_dict(r) for r in rows]
    filtered_tags = load_settings().get('filtered_tags') or []
    if filtered_tags:
        art = [a for a in art
               if not helpers.check_if_any_one_of_the_given_tags_exist(a, filtered_tags)]
    return art


@app.route('/art/all')
def get_all_art():
    sort_by = request.args.get('sort_by')
    try:    count  = int(request.args.get('count', 51))
    except (ValueError, TypeError): count  = 51
    try:    offset = int(request.args.get('offset', 0))
    except (ValueError, TypeError): offset = 0

    g.db = connect_db()
    art  = get_all_art_data(g.db, sort_by=sort_by, count=count, offset=offset)
    g.db.close()
    return jsonify(art)

@app.route('/art/all/count')
def get_all_art_count():
    g.db  = connect_db()
    count = g.db.execute('SELECT COUNT(id) FROM art').fetchone()[0]
    g.db.close()
    return jsonify(count)

@app.route('/art/<id>')
def get_art(id):
    try:    int(id)
    except ValueError: return redirect('/')

    g.db = connect_db()
    row  = g.db.execute(f'{_BASE_ART_SELECT} WHERE a.id = ?', [id]).fetchone()
    g.db.close()
    if row is None:
        return redirect('/')
    return render_template('art.html', art=_row_to_art_dict(row))

@app.route('/art/add', methods=['POST'])
def add_art():
    title             = request.form.get('title')
    images_from_files = request.files.getlist('image-from-file')
    images_from_urls  = request.form.getlist('image-from-url')
    images = []

    for local_image in request.form.getlist('local-image'):
        if local_image == 'true':
            file = images_from_files.pop(0)
            if file.filename == '':
                flash('No file selected', 'error'); return redirect('/')
            if file and helpers.allowed_file(file.filename, ALLOWED_EXTENSIONS):
                filename = helpers.prepend_date_time_to_string(secure_filename(file.filename))
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                images.append(filename)
            else:
                flash('File extension not allowed', 'error'); return redirect('/')
        elif local_image == 'false':
            url = images_from_urls.pop(0)
            if url:
                images.append(helpers.download(url, UPLOAD_FOLDER))
            else:
                flash('Image url was empty', 'error'); return redirect('/')

    g.db = connect_db()
    if request.form.get('existing-artist') == 'true':
        artist_id = request.form.get('artist-id')
    else:
        cursor    = g.db.execute('INSERT INTO artist(name,website) VALUES(?,?)',
                                 (request.form.get('artist-name'), request.form.get('artist-website')))
        artist_id = cursor.lastrowid

    cursor = g.db.execute('INSERT INTO art(title,artist_id,source) VALUES(?,?,?)',
                          (title, artist_id, request.form.get('source')))
    art_id = cursor.lastrowid

    for pos, url in enumerate(images):
        g.db.execute('INSERT INTO art_image(art_id,url,position) VALUES(?,?,?)', (art_id, url, pos))

    for tag in request.form.getlist('tags'):
        g.db.execute('INSERT INTO art_tag(art_id,tag_id) VALUES(?,?)', (art_id, tag))

    g.db.commit(); g.db.close()
    return redirect(f'/art/{art_id}')

@app.route('/art/edit', methods=['POST'])
def edit_art():
    id                = request.form.get('id')
    title             = request.form.get('title')
    images_from_files = request.files.getlist('image-from-file')
    images_from_urls  = request.form.getlist('image-from-url')
    existing_images   = request.form.getlist('existing-image')
    images = []

    for local_image in request.form.getlist('local-image'):
        if local_image == 'true':
            file = images_from_files.pop(0)
            if file.filename == '':
                flash('No file selected', 'error'); return redirect('/')
            if file and helpers.allowed_file(file.filename, ALLOWED_EXTENSIONS):
                filename = helpers.prepend_date_time_to_string(secure_filename(file.filename))
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                images.append(filename)
            else:
                flash('File extension not allowed', 'error'); return redirect('/')
        elif local_image == 'false':
            url = images_from_urls.pop(0)
            if url:
                images.append(helpers.download(url, UPLOAD_FOLDER))
            else:
                flash('Image url was empty', 'error'); return redirect('/')
        elif local_image == 'existing':
            images.append(existing_images.pop(0))

    g.db = connect_db()
    if request.form.get('existing-artist') == 'true':
        artist_id = request.form.get('artist-id')
    else:
        cursor    = g.db.execute('INSERT INTO artist(name,website) VALUES(?,?)',
                                 (request.form.get('artist-name'), request.form.get('artist-website')))
        artist_id = cursor.lastrowid

    old_urls = {r['url'] for r in g.db.execute('SELECT url FROM art_image WHERE art_id=?', [id]).fetchall()}
    for url in old_urls - set(images):
        try: os.remove(os.path.join(UPLOAD_FOLDER, url))
        except Exception: pass

    g.db.execute('UPDATE art SET title=?,artist_id=?,source=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
                 (title, artist_id, request.form.get('source'), id))
    g.db.execute('DELETE FROM art_image WHERE art_id=?', [id])
    for pos, url in enumerate(images):
        g.db.execute('INSERT INTO art_image(art_id,url,position) VALUES(?,?,?)', (id, url, pos))

    g.db.execute('DELETE FROM art_tag WHERE art_id=?', [id])
    for tag in request.form.getlist('tags'):
        g.db.execute('INSERT INTO art_tag(art_id,tag_id) VALUES(?,?)', (id, tag))

    g.db.commit(); g.db.close()
    flash('Art updated', 'success')
    return redirect(f'/art/{id}')

@app.route('/art/delete', methods=['POST'])
def delete_art():
    id   = request.form.get('id')
    g.db = connect_db()
    for r in g.db.execute('SELECT url FROM art_image WHERE art_id=?', [id]).fetchall():
        try: os.remove(os.path.join(UPLOAD_FOLDER, r['url']))
        except Exception: pass
    g.db.execute('PRAGMA foreign_keys=on')
    g.db.execute('DELETE FROM art WHERE id=?', [id])
    g.db.commit(); g.db.close()
    flash('Art deleted', 'success')
    return redirect('/')

@app.route('/art/image/delete', methods=['POST'])
def delete_art_image():
    id        = request.form.get('id')
    image_url = request.form.get('image_url')
    g.db      = connect_db()
    try: os.remove(os.path.join(UPLOAD_FOLDER, image_url))
    except Exception: pass
    try:
        g.db.execute('DELETE FROM art_image WHERE art_id=? AND url=?', [id, image_url])
        g.db.execute('UPDATE art SET updated_at=CURRENT_TIMESTAMP WHERE id=?', [id])
        g.db.commit()
        flash('Art image deleted', 'success')
    except Exception:
        flash('Art image not found', 'error')
    finally:
        g.db.close()
        return redirect(f'/art/{id}')

@app.route('/artist/all')
def get_all_artists():
    g.db = connect_db()
    cursor = g.db.execute('SELECT * FROM artist')
    artists = [dict(id=row[0], name=row[1], website=row[2], added_at=row[3], updated_at=row[4]) for row in cursor.fetchall()]
    g.db.close()
    return jsonify(artists)

@app.route('/tag/all')
def get_all_tags():
    g.db = connect_db()
    cursor = g.db.execute('SELECT * FROM tag')
    artists = [dict(id=row[0], name=row[1], added_at=row[2], updated_at=row[3]) for row in cursor.fetchall()]
    g.db.close()
    return jsonify(artists)

# start /add

@app.route('/add')
def add():
    return render_template('add.html')

def add_from(request, prefix_lower, prefix_normal, multi=False):
    url = request.form.get(f'{prefix_lower}-art-url')
    if url is None and request.get_json():
        url = request.get_json().get(f'{prefix_lower}-art-url')

    if not url:
        if helpers.request_wants_json():
            return jsonify(status='error', message=f'{prefix_normal} Image url was empty')
        flash(f'{prefix_normal} Image url was empty', 'error')
        return redirect('/add')

    scraper_map = {
        'deviantart': lambda: scrapers.deviant_art(url),
        'artstation': lambda: scrapers.art_station(url, multi),
        'pixiv':      lambda: scrapers.pixiv(url, load_settings().get('pixiv_username'),
                                             load_settings().get('pixiv_password')),
        'tumblr':     lambda: scrapers.tumblr(url),
        'instagram':  lambda: scrapers.instagram(url),
        'reddit':     lambda: scrapers.reddit(url),
        'twitter':    lambda: scrapers.twitter(url),
    }
    art = scraper_map[prefix_lower]()

    if multi:
        images = [helpers.download(img_url, UPLOAD_FOLDER) for img_url in art['image_url']]
    elif prefix_lower == 'pixiv':
        images = [helpers.download(art['image_url'], UPLOAD_FOLDER, art['source'])]
    else:
        images = [helpers.download(art['image_url'], UPLOAD_FOLDER)]

    g.db = connect_db()
    if request.form.get('existing-artist'):
        artist_id = request.form.get('artist-id')
    else:
        row = g.db.execute('SELECT id FROM artist WHERE website=?', [art['artist_website']]).fetchone()
        if row:
            artist_id = row['id']
        else:
            cursor    = g.db.execute('INSERT INTO artist(name,website) VALUES(?,?)',
                                     (art['artist_name'], art['artist_website']))
            artist_id = cursor.lastrowid

    cursor = g.db.execute('INSERT INTO art(title,artist_id,source) VALUES(?,?,?)',
                          (art['title'], artist_id, art['source']))
    art_id = cursor.lastrowid

    for pos, img_url in enumerate(images):
        g.db.execute('INSERT INTO art_image(art_id,url,position) VALUES(?,?,?)', (art_id, img_url, pos))

    g.db.commit(); g.db.close()

    if helpers.request_wants_json():
        return jsonify(status='success', message='Art added', id=art_id)
    flash('Art added', 'success')
    return redirect(f'/art/{art_id}')

@app.route('/add-from-deviantart', methods=['POST'])
def add_from_deviantart():
    return add_from(request, 'deviantart', 'DeviantArt')

@app.route('/add-from-artstation', methods=['POST'])
def add_from_artstation():
    return add_from(request, 'artstation', 'ArtStation')

@app.route('/add-from-artstation-all', methods=['POST'])
def add_from_artstation_all():
    return add_from(request, 'artstation', 'ArtStation', True)

@app.route('/add-from-pixiv', methods=['POST'])
def add_from_pixiv():
    return add_from(request, 'pixiv', 'Pixiv')

@app.route('/add-from-tumblr', methods=['POST'])
def add_from_tumblr():
    return add_from(request, 'tumblr', 'Tumblr')

@app.route('/add-from-instagram', methods=['POST'])
def add_from_instagram():
    return add_from(request, 'instagram', 'Instagram')

@app.route('/add-from-reddit', methods=['POST'])
def add_from_reddit():
    return add_from(request, 'reddit', 'Reddit')

@app.route('/add-from-twitter', methods=['POST'])
def add_from_twitter():
    return add_from(request, 'twitter', 'Twitter')

# end /add

# start /tag-manager

@app.route('/tag-manager')
def tag_manager():
    g.db = connect_db()
    tags = [dict(id=r['id'], name=r['name'], added_at=r['created_at'], updated_at=r['updated_at'])
            for r in g.db.execute('SELECT * FROM tag').fetchall()]
    for tag in tags:
        tag['art_count'] = g.db.execute(
            'SELECT count(*) FROM art_tag WHERE tag_id=?', [tag['id']]
        ).fetchone()[0]
    g.db.close()
    return render_template('tag-manager.html', tags=tags)

@app.route('/tag/add', methods=['POST'])
def add_tag():
    name = request.form.get('name')
    g.db = connect_db()
    g.db.execute('INSERT INTO tag(name) VALUES(?)', [name])
    g.db.commit()
    g.db.close()
    flash('Tag added', 'success')
    return redirect('/tag-manager')

@app.route('/tag/edit', methods=['POST'])
def edit_tag():
    id = request.form.get('id')
    name = request.form.get('name')
    g.db = connect_db()
    g.db.execute('UPDATE tag SET name=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', [name, id])
    g.db.commit()
    g.db.close()
    flash('Tag updated', 'success')
    return redirect('/tag-manager')

@app.route('/tag/delete', methods=['POST'])
def delete_tag():
    id = request.form.get('id')
    g.db = connect_db()
    g.db.execute('PRAGMA foreign_keys=on')
    g.db.execute('DELETE FROM tag WHERE id=?', [id])
    g.db.commit()
    g.db.close()
    flash('Tag deleted', 'success')
    return redirect('/tag-manager')

# end /tag-manager

# start /artist-manager

@app.route('/artist-manager')
def artist_manager():
    g.db    = connect_db()
    artists = [dict(id=r['id'], name=r['name'], website=r['website'],
                    added_at=r['created_at'], updated_at=r['updated_at'])
               for r in g.db.execute('SELECT * FROM artist').fetchall()]
    for artist in artists:
        artist['art_count'] = g.db.execute(
            'SELECT count(*) FROM art WHERE artist_id=?', [artist['id']]
        ).fetchone()[0]
    g.db.close()
    return render_template('artist-manager.html', artists=artists)

@app.route('/artist/add', methods=['POST'])
def add_artist():
    name = request.form.get('name')
    website = request.form.get('website')
    g.db = connect_db()
    g.db.execute('INSERT INTO artist(name, website) VALUES(?, ?)', [name, website])
    g.db.commit()
    g.db.close()
    flash('Artist added', 'success')
    return redirect('/artist-manager')

@app.route('/artist/edit', methods=['POST'])
def edit_artist():
    id = request.form.get('id')
    name = request.form.get('name')
    website = request.form.get('website')
    g.db = connect_db()
    g.db.execute('UPDATE artist SET name=?, website=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', [name, website, id])
    g.db.commit()
    g.db.close()
    flash('Artist updated', 'success')
    return redirect('/artist-manager')

@app.route('/artist/delete', methods=['POST'])
def delete_artist():
    id   = request.form.get('id')
    g.db = connect_db()
    for r in g.db.execute(
        'SELECT ai.url FROM art_image ai JOIN art a ON ai.art_id=a.id WHERE a.artist_id=?', [id]
    ).fetchall():
        try: os.remove(os.path.join(UPLOAD_FOLDER, r['url']))
        except Exception: pass
    g.db.execute('PRAGMA foreign_keys=on')
    g.db.execute('DELETE FROM artist WHERE id=?', [id])
    g.db.commit(); g.db.close()
    flash('Artist deleted', 'success')
    return redirect('/artist-manager')

# end /artist-manager

# start /settings

@app.route('/settings')
def settings():
    s = load_settings()
    settings_out = dict(
        layout         = s.get('layout'),
        pixiv_username = s.get('pixiv_username') or '',
        pixiv_password = s.get('pixiv_password') or '',
        filtered_tags  = s.get('filtered_tags')  or [],
    )
    g.db = connect_db()
    tags = [dict(id=r['id'], name=r['name'], added_at=r['created_at'], updated_at=r['updated_at'])
            for r in g.db.execute('SELECT * FROM tag').fetchall()]
    g.db.close()
    return render_template('settings.html', settings=settings_out, tags=tags)

@app.route('/settings', methods=['POST'])
def update_settings():
    layout = request.form.get('layout')
    pixiv_username = request.form.get('pixiv_username')
    pixiv_password = request.form.get('pixiv_password')
    filtered_tags = request.form.getlist('filtered_tags')

    settings = load_settings()

    settings.set('layout', layout)

    if pixiv_username != '':
        settings.set('pixiv_username', pixiv_username)
    else:
        if settings.get('pixiv_username') != None:
            settings.rem('pixiv_username')

    if pixiv_password != '':
        settings.set('pixiv_password', pixiv_password)
    else:
        if settings.get('pixiv_password') != None:
            settings.rem('pixiv_password')

    if filtered_tags != []:
        settings.set('filtered_tags', filtered_tags)
    else:
        try:
            settings.rem('filtered_tags')
        except:
            pass # 'filtered_tags' key doesn't exist that's why

    settings.save()

    flash('Settings updated', 'success')
    return redirect('/settings')

# end /settings

def get_filter_results(filters, db):
    tag_ids    = None
    artist_ids = None

    for f in filters:
        key   = (f[0] or f[2]).lower()
        value = (f[1] or f[3])

        if key == 'tag':
            terms  = [t.strip() for t in helpers.escape_for_sql(value).split(',')]
            where  = ' OR '.join('name LIKE ?' for _ in terms)
            rows   = db.execute(
                f'SELECT DISTINCT art_id FROM art_tag_view WHERE {where}',
                [f'%{t}%' for t in terms]
            ).fetchall()
            tag_ids = {r['art_id'] for r in rows}

        elif key == 'artist':
            terms  = [t.strip() for t in helpers.escape_for_sql(value).split(',')]
            where  = ' OR '.join('ar.name LIKE ?' for _ in terms)
            rows   = db.execute(
                f'SELECT a.id FROM art a JOIN artist ar ON a.artist_id = ar.id WHERE {where}',
                [f'%{t}%' for t in terms]
            ).fetchall()
            artist_ids = {r['id'] for r in rows}

    if tag_ids is not None and artist_ids is not None:
        ids = tag_ids & artist_ids
    elif tag_ids is not None:
        ids = tag_ids
    elif artist_ids is not None:
        ids = artist_ids
    else:
        return []

    return [{'art_id': art_id} for art_id in ids]

def _search_conditions(query):
    """Parse query string -> (filter_results, search_term, db)."""
    regex   = r'(\w+):\"(.*?)\"|(\w+):(\w+)'
    filters = re.findall(regex, query)
    term    = helpers.escape_for_sql(re.sub(regex, '', query).strip())
    db      = connect_db()
    return get_filter_results(filters, db), term, db


def get_search_results(query, count=51, offset=0):
    filter_results, term, db = _search_conditions(query)

    conds, params = [], []
    if filter_results:
        conds.append(f"a.id IN ({','.join('?' for _ in filter_results)})")
        params.extend(r['art_id'] for r in filter_results)
    if term:
        conds.append('a.title LIKE ?')
        params.append(f'%{term}%')
    if not conds:
        db.close()
        return []

    where = ' AND '.join(conds)
    params.extend([count, offset])
    rows = db.execute(
        f'{_BASE_ART_SELECT} WHERE {where} ORDER BY a.updated_at DESC LIMIT ? OFFSET ?',
        params
    ).fetchall()
    db.close()
    return [_row_to_art_dict(r) for r in rows]


def get_search_results_count(query):
    filter_results, term, db = _search_conditions(query)

    conds, params = [], []
    if filter_results:
        conds.append(f"a.id IN ({','.join('?' for _ in filter_results)})")
        params.extend(r['art_id'] for r in filter_results)
    if term:
        conds.append('a.title LIKE ?')
        params.append(f'%{term}%')
    if not conds:
        db.close()
        return 0

    where = ' AND '.join(conds)
    count = db.execute(
        f'SELECT COUNT(*) FROM ({_BASE_ART_SELECT} WHERE {where}) AS sub', params
    ).fetchone()[0]
    db.close()
    return count


@app.route('/search_json')
def search_json():
    query = request.args.get('q')
    try:    count  = int(request.args.get('count',  51))
    except: count  = 51
    try:    offset = int(request.args.get('offset', 0))
    except: offset = 0
    return jsonify(get_search_results(query, count=count, offset=offset) if query else [])


@app.route('/search_json/count')
def search_json_count():
    query = request.args.get('q')
    return jsonify(get_search_results_count(query) if query else 0)

@app.route('/search')
def search():
    query = request.args.get('q')
    art   = get_search_results(query, count=51) if query else []
    return render_template('search.html', art=art, search_query=query,
                           layout=load_settings().get('layout'))

_BASE_ART_SELECT = '''
    SELECT
        a.id,  a.title,  a.source,
        a.created_at  AS added_on,
        a.updated_at  AS last_updated_on,
        a.artist_id,
        ar.name       AS artist_name,
        ar.website    AS artist_website,
        img.image_urls,
        tgs.tag_ids,
        tgs.tag_names
    FROM art a
    LEFT JOIN artist ar ON a.artist_id = ar.id
    LEFT JOIN (
        SELECT art_id, GROUP_CONCAT(url) AS image_urls
        FROM (SELECT art_id, url FROM art_image ORDER BY art_id, position)
        GROUP BY art_id
    ) img ON a.id = img.art_id
    LEFT JOIN (
        SELECT at.art_id,
               GROUP_CONCAT(t.id)   AS tag_ids,
               GROUP_CONCAT(t.name) AS tag_names
        FROM art_tag at JOIN tag t ON at.tag_id = t.id
        GROUP BY at.art_id
    ) tgs ON a.id = tgs.art_id
'''


def _row_to_art_dict(row):
    tag_ids   = row['tag_ids'].split(',')   if row['tag_ids']   else []
    tag_names = row['tag_names'].split(',') if row['tag_names'] else []
    return {
        'id':              row['id'],
        'title':           row['title'],
        'image_url':       row['image_urls'].split(',') if row['image_urls'] else [],
        'source':          row['source'],
        'added_on':        row['added_on'],
        'artist_id':       row['artist_id'],
        'artist_name':     row['artist_name'],
        'artist_website':  row['artist_website'],
        'last_updated_on': row['last_updated_on'],
        'tags':            [{'tag_id': int(tid), 'tag_name': tname}
                            for tid, tname in zip(tag_ids, tag_names)],
    }


def connect_db():
    conn = sqlite3.connect(app.database)
    conn.row_factory = sqlite3.Row
    return conn

class Settings:
    def __init__(self, file_path):
        self.file_path = file_path
        try:
            with open(file_path, 'r') as json_file:
                self.data = json.load(json_file)
        except:
            with open(file_path, "w") as json_file:
                json_file.write('{}')
            with open(file_path, 'r') as json_file:
                self.data = json.load(json_file)
    
    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def rem(self, key):
        del self.data[key]

    def save(self):
        with open(self.file_path, "w") as json_file:
            json_file.write(json.dumps(self.data, indent = 4))

def load_settings():
    if 'settings' not in g:
        g.settings = Settings(app.settings_database)
    return g.settings

if __name__ == '__main__':
    app.run(host= '0.0.0.0', port=9874, threaded=True)
