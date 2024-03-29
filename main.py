from flask import Flask, jsonify, render_template, request, redirect, g, flash
import helpers, sqlite3, os, re, json, requests, scrapers
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/images/'
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'svg'])

app = Flask(__name__)

app.secret_key = 'some_secret'
app.database = 'store.db'
app.database = os.path.join(os.path.dirname(__file__), app.database)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.settings_database = 'settings.json'
app.settings_database = os.path.join(os.path.dirname(__file__), app.settings_database)

# app.debug = True

@app.route('/')
def index():
    try:
        response = requests.get(request.url_root + 'art/all?count=51')
    except requests.ConnectionError:
       return "Connection Error"
    art = json.loads(response.text)
    layout = load_settings().get('layout')
    return render_template('index.html', art=art, layout=layout)

@app.route('/art/all')
def get_all_art():
    sort_by = request.args.get('sort_by')
    count = request.args.get('count')
    offset = request.args.get('offset')

    g.db = connect_db()

    sql_query = 'SELECT * FROM art_artist_view '
    if sort_by == 'title':
        sql_query += 'ORDER BY TITLE DESC '
    else:
        sql_query += 'ORDER BY updated_at DESC '
    if count != None:
        try:
            int(count) # check if count is an integer
        except ValueError: # if no then
            count = None
        else: # if yes then
            sql_query += 'LIMIT '+ count + ' '
    if offset != None:
        try:
            int(offset) # check if offset is an integer
        except ValueError: # if no then
            offset = None
        else: # if yes then
            sql_query += 'OFFSET '+ offset

    art = g.db.execute(sql_query) # art_artist_view is basically the art table left joined with the artist table
    art = [dict(id=row[0], title=row[1], image_url=row[2], source=row[3], added_on=row[4], artist_id=row[5], artist_name=row[6], artist_website=row[7], last_updated_on=row[8], tags=[]) for row in art.fetchall()]
    # check specific view for the order of the columns used above

    tags = g.db.execute('SELECT * FROM art_tag_view') # art_tag_view is basically the art_tag table left joined with the tag table
    tags = [dict(id=row[0], art_id=row[1], tag_id=row[2], tag_name=row[3]) for row in tags.fetchall()]

    for single_art in art:
        for tag in tags:
            if tag['art_id'] == single_art['id']:
                single_art['tags'] += [tag]

    filtered_tags = load_settings().get('filtered_tags')
    
    if filtered_tags is None:
        filtered_tags = []

    if filtered_tags != []:
        art[:] = [single_art for single_art in art if not helpers.check_if_any_one_of_the_given_tags_exist(single_art, filtered_tags)]

    for single_art in art:
        single_art['image_url'] = single_art['image_url'].split(',')

    g.db.close()

    return jsonify(art)

@app.route('/art/all/count')
def get_all_art_count():
    g.db = connect_db()
    count = g.db.execute('SELECT COUNT(id) FROM art_artist_view').fetchone()[0]
    g.db.close()
    return jsonify(count)

@app.route('/art/<id>')
def get_art(id):
    try:
        int(id) # check if id is an integer
    except ValueError: # if no then
        return redirect('/')
    else: # if yes then
        g.db = connect_db()

        art = g.db.execute('SELECT * FROM art_artist_view where id=?', [id]).fetchone()
        if art != None:
            art = dict(id=art[0], title=art[1], image_url=art[2], source=art[3], added_on=art[4], artist_id=art[5], artist_name=art[6], artist_website=art[7], last_updated_on=art[8], tags=[])

            tags = g.db.execute('SELECT * FROM art_tag_view')
            tags = [dict(id=row[0], art_id=row[1], tag_id=row[2], tag_name=row[3]) for row in tags.fetchall()]

            # attach all associated tags to the art
            for tag in tags:
                if tag['art_id'] == art['id']:
                    art['tags'] += [tag]

            art['image_url'] = art['image_url'].split(',')

            g.db.close()
            return render_template('art.html', art=art)
        else:
            return redirect('/')

@app.route('/art/add', methods=['POST'])
def add_art():
    title = request.form.get('title')

    images_from_files = request.files.getlist('image-from-file')
    images_from_urls = request.form.getlist('image-from-url')
    images = []
    for local_image in request.form.getlist('local-image'):
        if local_image == 'true':
            file = images_from_files[0]
            images_from_files.pop(0)
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect('/')
            if file and helpers.allowed_file(file.filename, ALLOWED_EXTENSIONS):
                filename = secure_filename(file.filename)
                filename = helpers.prepend_date_time_to_string(filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename
                images.append(image)
            else:
                flash('File extension not allowed', 'error')
                return redirect('/')
        elif local_image == 'false':
            image = images_from_urls[0]
            images_from_urls.pop(0)
            if image != '':
                image = helpers.download(image, UPLOAD_FOLDER)
                images.append(image)
            else:
                flash('Image url was empty', 'error')
                return redirect('/')

    images_string = ','.join(images)

    g.db = connect_db()

    if request.form.get('existing-artist') == 'true':
        artist_id = request.form.get('artist-id')
    else:
        artist_name = request.form.get('artist-name')
        artist_website = request.form.get('artist-website')
        cursor = g.db.execute('INSERT into artist(name, website) VALUES(?,?)', (artist_name, artist_website))
        artist_id = cursor.lastrowid

    source = request.form.get('source')
    
    cursor = g.db.execute('INSERT into art(title, image_url, artist_id, source) VALUES(?,?,?,?)', (title, images_string, artist_id, source))
    art_id = cursor.lastrowid
    
    tags = request.form.getlist('tags')
    if tags != []:
        for tag in tags:
            g.db.execute('INSERT into art_tag(art_id, tag_id) VALUES(?, ?)', (art_id, tag))

    g.db.commit()
    g.db.close()

    return redirect('/art/' + str(art_id))

@app.route('/art/edit', methods=['POST'])
def edit_art():
    id = request.form.get('id')

    title = request.form.get('title')

    images_from_files = request.files.getlist('image-from-file')
    images_from_urls = request.form.getlist('image-from-url')
    existing_images = request.form.getlist('existing-image')
    images = []
    for local_image in request.form.getlist('local-image'):
        if local_image == 'true':
            file = images_from_files[0]
            images_from_files.pop(0)
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect('/')
            if file and helpers.allowed_file(file.filename, ALLOWED_EXTENSIONS):
                filename = secure_filename(file.filename)
                filename = helpers.prepend_date_time_to_string(filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename
                images.append(image)
            else:
                flash('File extension not allowed', 'error')
                return redirect('/')
        elif local_image == 'false':
            image = images_from_urls[0]
            images_from_urls.pop(0)
            if image != '':
                image = helpers.download(image, UPLOAD_FOLDER)
                images.append(image)
            else:
                flash('Image url was empty', 'error')
                return redirect('/')
        elif local_image == 'existing':
            image = existing_images[0]
            existing_images.pop(0)
            images.append(image)

    images_string = ','.join(images)

    g.db = connect_db()

    if request.form.get('existing-artist') == 'true':
        artist_id = request.form.get('artist-id')
    else:
        artist_name = request.form.get('artist-name')
        artist_website = request.form.get('artist-website')
        cursor = g.db.execute('INSERT into artist(name, website) VALUES(?,?)', (artist_name, artist_website))
        artist_id = cursor.lastrowid

    source = request.form.get('source')

    images_before_edit = g.db.execute('SELECT image_url FROM art WHERE id=?', [id]).fetchone()[0]
    images_before_edit = images_before_edit.split(',')
    images_that_are_no_longer_in_use = list(set(images_before_edit) - set(images))
    for image_that_is_no_longer_in_use in images_that_are_no_longer_in_use:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, image_that_is_no_longer_in_use))
        except Exception as e:
            # print(e)
            pass

    g.db.execute('UPDATE art SET title=?, image_url=?, artist_id=?, source=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (title, images_string, artist_id, source, id))
    
    tags = request.form.getlist('tags')
    g.db.execute('DELETE FROM art_tag WHERE art_id=?', [id])
    if tags != []:
        for tag in tags:
            g.db.execute('INSERT into art_tag(art_id, tag_id) VALUES(?, ?)', (id, tag))
    
    g.db.commit()
    g.db.close()

    flash('Art updated', 'success')
    return redirect('/art/' + id)

@app.route('/art/delete', methods=['POST'])
def delete_art():
    id = request.form.get('id')
    g.db = connect_db()
    image_filenames = g.db.execute('SELECT image_url FROM art WHERE id=?', [id]).fetchone()[0]
    image_filenames = image_filenames.split(',')
    for image_filename in image_filenames:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, image_filename)) # delete image
        except Exception as e:
            # print(e)
            # this gives a false positive when images added from edit-art are deleted - I've checked, the errored file does get deleted, so the error doesn't make any sense
            # flash('Image belonging to the art was not found', 'error')
            pass
    g.db.execute('PRAGMA foreign_keys=on')
    g.db.execute('DELETE FROM art WHERE id=?', [id]) # delete record
    g.db.commit()
    g.db.close()
    flash('Art deleted', 'success')
    return redirect('/')

@app.route('/art/image/delete', methods=['POST'])
def delete_art_image():
    id = request.form.get('id')
    image_url = request.form.get('image_url')
    g.db = connect_db()
    image_filenames = g.db.execute('SELECT image_url FROM art WHERE id=?', [id]).fetchone()[0]
    image_filenames = image_filenames.split(',')
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, image_url)) # delete image
        image_filenames.remove(image_url)
        g.db.execute('UPDATE art SET image_url=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (','.join(image_filenames), id))
        g.db.commit()
        g.db.close()
        flash('Art image deleted', 'success')
    except Exception as e:
        # print(e)
        flash('Art image not found', 'error')
    finally:
        return redirect('/art/' + id)

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
    if url == None and request.get_json() != None:
        url = request.get_json()[f'{prefix_lower}-art-url']
    if url != '' and url != None:
        if prefix_lower == 'deviantart':
            art = scrapers.deviant_art(url)
        elif prefix_lower == 'artstation':
            if multi:
                art = scrapers.art_station(url, True)
            else:
                art = scrapers.art_station(url)
        elif prefix_lower == 'pixiv':
            art = scrapers.pixiv(url, load_settings().get('pixiv_username'), load_settings().get('pixiv_password'))
        elif prefix_lower == 'tumblr':
            art = scrapers.tumblr(url)
        elif prefix_lower == 'instagram':
            art = scrapers.instagram(url)
        elif prefix_lower == 'reddit':
            art = scrapers.reddit(url)
        elif prefix_lower == 'twitter':
            art = scrapers.twitter(url)

        title = art['title']
        if multi:
            images = []
            for image_url in art['image_url']:
                images.append(helpers.download(image_url, UPLOAD_FOLDER))
            images = ','.join(images)
            image = images
        else:
            if prefix_lower == 'pixiv':
                image = helpers.download(art['image_url'], UPLOAD_FOLDER, art['source'])
            else:
                image = helpers.download(art['image_url'], UPLOAD_FOLDER)
        source = art['source']
        artist_name = art['artist_name']
        artist_website = art['artist_website']

        g.db = connect_db()

        if request.form.get('existing-artist'):
            artist_id = request.form.get('artist-id')
        else:
            artist = g.db.execute('SELECT id FROM artist WHERE website=?', [artist_website]).fetchone()
            if artist != None:
                artist_id = artist[0]
            else:
                cursor = g.db.execute('INSERT into artist(name, website) VALUES(?,?)', (artist_name, artist_website))
                artist_id = cursor.lastrowid

        cursor = g.db.execute('INSERT into art(title, image_url, artist_id, source) VALUES(?,?,?,?)', (title, image, artist_id, source))

        inserted_row_id = cursor.lastrowid

        g.db.commit()
        g.db.close()

        if helpers.request_wants_json():
            return jsonify(status='success', message='Art added', id=inserted_row_id)
        else:
            flash('Art added', 'success')
    else:
        if helpers.request_wants_json():
            return jsonify(status='error', message=f'{prefix_normal} Image url was empty')
        else:
            flash(f'{prefix_normal} Image url was empty', 'error')
            return redirect('/add')

    if not helpers.request_wants_json():
        return redirect('/art/' + str(inserted_row_id))

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
    try:
        response = requests.get(request.url_root + 'tag/all')
    except requests.ConnectionError:
       return "Connection Error"
    tags = json.loads(response.text)

    g.db = connect_db()
    for tag in tags:
        tag['art_count'] = g.db.execute('SELECT count(*) from art_tag WHERE tag_id=?', [tag['id']]).fetchone()[0]
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
    try:
        response = requests.get(request.url_root + 'artist/all')
    except requests.ConnectionError:
       return "Connection Error"
    artists = json.loads(response.text)
    
    g.db = connect_db()
    for artist in artists:
        artist['art_count'] = g.db.execute('SELECT count(*) from art WHERE artist_id=?', [artist['id']]).fetchone()[0]
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
    id = request.form.get('id')

    g.db = connect_db()

    image_filenames = g.db.execute('SELECT image_url FROM art WHERE artist_id=?', [id]).fetchall()
    for image_filename in image_filenames:
        image_filename = image_filename[0]
        if os.path.isfile(os.path.join(UPLOAD_FOLDER, image_filename)):
            os.remove(os.path.join(UPLOAD_FOLDER, image_filename)) # delete image

    g.db.execute('PRAGMA foreign_keys=on')
    g.db.execute('DELETE FROM artist WHERE id=?', [id])
    g.db.commit()

    g.db.close()

    flash('Artist deleted', 'success')
    return redirect('/artist-manager')

# end /artist-manager

# start /settings

@app.route('/settings')
def settings():
    settings = load_settings()
    layout = settings.get('layout')
    pixiv_username = settings.get('pixiv_username') if settings.get('pixiv_username') else ''
    pixiv_password = settings.get('pixiv_password') if settings.get('pixiv_password') else ''
    filtered_tags = settings.get('filtered_tags')
    if filtered_tags is None:
        filtered_tags = []
    
    settings_to_return = dict(layout=layout, pixiv_username=pixiv_username, pixiv_password=pixiv_password, filtered_tags=filtered_tags)

    try:
        response = requests.get(request.url_root + 'tag/all')
    except requests.ConnectionError:
       return "Connection Error"
    tags = json.loads(response.text)

    return render_template('settings.html', settings=settings_to_return, tags=tags)

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
    match = 0
    # filter[0] & filter[1] return group 1 & 2's results --> (\w+):\"(.*?)\"
    # filter[2] & filter[3] return group 3 & 4's results --> (\w+):(\w+)
    # so you need to check both group sets
    for filter in filters:
        if filter[0] == 'tag' or filter[2] == 'tag':
            tags = filter[1] + filter[3]
            tags = helpers.escape_for_sql(tags)
            tags = [x.strip() for x in tags.split(',')]
            sql_query = 'SELECT DISTINCT art_id FROM art_tag_view WHERE ' + ' or '.join(('name LIKE ' + str("'%"+n+"%'") for n in tags))
            art_belonging_to_tags = g.db.execute(sql_query).fetchall()
            filter_results = [dict(art_id=row[0]) for row in art_belonging_to_tags]
            match +=1
        if filter[0] == 'artist' or filter[2] == 'artist':
            artists = filter[1] + filter[3]
            artists = helpers.escape_for_sql(artists)
            artists = [x.strip() for x in artists.split(',')]
            sql_query = 'SELECT id FROM art_artist_view WHERE ' + ' or '.join(('name LIKE ' + str("'%"+n+"%'") for n in artists))
            art_belonging_to_artists = g.db.execute(sql_query).fetchall()
            filter_results = [dict(art_id=row[0]) for row in art_belonging_to_artists]
            match +=1
        if match == 2: # if both filters exist then apply this
            filter_results = set(art_belonging_to_tags).intersection(set(art_belonging_to_artists))
            filter_results = [dict(art_id=row[0]) for row in filter_results]

    return filter_results

def get_search_results(query, sql_to_append):
    filter_matching_regex = r'(\w+):\"(.*?)\"|(\w+):(\w+)' # test string:- tag:people artist:"guy, girl, super dad, super mom"
    filters = re.findall(filter_matching_regex, query) # returns a list
    search_term = re.sub(filter_matching_regex,'', query) # return a string
    search_term = search_term.strip() # we don't want an empty string filled with a space or spaces
    search_term = helpers.escape_for_sql(search_term)

    g.db = connect_db()

    filter_results = get_filter_results(filters, g.db)

    if 'filter_results' in locals() and filter_results != []: # if filter results exist
        sql_query = 'SELECT * FROM art_artist_view WHERE ' + ' or '.join(('id = ' + str("'"+str(result['art_id'])+"'") for result in filter_results))
        if search_term != '':
            sql_query = f'SELECT * FROM ({sql_query}) WHERE title LIKE "%{search_term}%"'
        sql_query += sql_to_append
        search_results = g.db.execute(sql_query).fetchall()
        search_results = [dict(id=row[0], title=row[1], image_url=row[2], source=row[3], added_on=row[4], artist_id=row[5], artist_name=row[6], artist_website=row[7], last_updated_on=row[8], tags=[]) for row in search_results]

        # get the tags for the results
        art_tags = [dict(id=row[0], art_id=row[1], tag_id=row[2], tag_name=row[3]) for row in g.db.execute('SELECT * FROM art_tag_view').fetchall()]
        for art in search_results:
            for tag in art_tags:
                if tag['art_id'] == art['id']:
                    art['tags'] += [tag]

    else: # if no filter results exist
        if search_term != '':
            sql_query = 'SELECT * FROM art_artist_view WHERE title LIKE ' + "'%"+search_term+"%'"
            sql_query += sql_to_append
            search_results = g.db.execute(sql_query).fetchall()
            search_results = [dict(id=row[0], title=row[1], image_url=row[2], source=row[3], added_on=row[4], artist_id=row[5], artist_name=row[6], artist_website=row[7], last_updated_on=row[8], tags=[]) for row in search_results]

            # get the tags for the results
            art_tags = [dict(id=row[0], art_id=row[1], tag_id=row[2], tag_name=row[3]) for row in g.db.execute('SELECT * FROM art_tag_view').fetchall()]
            for art in search_results:
                for tag in art_tags:
                    if tag['art_id'] == art['id']:
                        art['tags'] += [tag]
        else:
            search_results = []

    for single_art in search_results:
        single_art['image_url'] = single_art['image_url'].split(',')

    g.db.close()

    return search_results

def get_search_results_count(query):
    filter_matching_regex = r'(\w+):\"(.*?)\"|(\w+):(\w+)' # test string:- tag:people artist:"guy, girl, super dad, super mom"
    filters = re.findall(filter_matching_regex, query) # returns a list
    search_term = re.sub(filter_matching_regex,'', query) # return a string
    search_term = search_term.strip() # we don't want an empty string filled with a space or spaces
    search_term = helpers.escape_for_sql(search_term)

    g.db = connect_db()

    filter_results = get_filter_results(filters, g.db)

    if 'filter_results' in locals() and filter_results != []: # if filter results exist
        sql_query = 'SELECT * FROM art_artist_view WHERE ' + ' or '.join(('id = ' + str("'"+str(result['art_id'])+"'") for result in filter_results))
        if search_term != '':
            sql_query = f'SELECT * FROM ({sql_query}) WHERE title LIKE "%{search_term}%"'
        search_results_count = g.db.execute(f'SELECT COUNT(id) FROM ({sql_query})').fetchone()[0]
    else: # if no filter results exist
        if search_term != '':
            sql_query = 'SELECT * FROM art_artist_view WHERE title LIKE ' + "'%"+search_term+"%'"
            search_results_count = g.db.execute(f'SELECT COUNT(id) FROM ({sql_query})').fetchone()[0]
        else:
            search_results_count = 0

    g.db.close()

    return search_results_count

@app.route('/search_json')
def search_json():
    query = request.args.get('q')
    count = request.args.get('count')
    offset = request.args.get('offset')

    order_by = ' ORDER BY updated_at DESC'

    sql_to_append = order_by

    if count != None:
        try:
            int(count) # check if count is an integer
        except ValueError: # if no then
            count = None
        else: # if yes then
            sql_to_append += ' LIMIT '+ count
    else:
        sql_to_append += ' LIMIT 51'
    if offset != None:
        try:
            int(offset) # check if offset is an integer
        except ValueError: # if no then
            offset = None
        else: # if yes then
            sql_to_append += ' OFFSET '+ offset

    if query:
        return jsonify(get_search_results(query, sql_to_append))
    else:
        return jsonify([])

@app.route('/search_json/count')
def search_json_count():
    query = request.args.get('q')
    if query:
        return jsonify(get_search_results_count(query))
    else:
        return jsonify([])

@app.route('/search')
def search():
    query = request.args.get('q')
    try:
        response = requests.get(request.url_root + f'search_json?q={query}&count=51')
    except requests.ConnectionError:
       return "Connection Error"
    search_results = json.loads(response.text)
    layout = load_settings().get('layout')
    return render_template('search.html', art=search_results, search_query=query, layout=layout)

def connect_db():
    return sqlite3.connect(app.database)

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
    return Settings(app.settings_database)

if __name__ == '__main__':
    app.run(host= '0.0.0.0', port=9874, threaded=True)
