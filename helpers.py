import requests, os, time
from urllib.parse import urlparse
from flask import request

def get_filename_from_url(url):
    return os.path.basename(urlparse(url).path)

def download(url, upload_dir, url_referer=None):
    try:
        if url_referer:
            response = requests.get(url, headers=dict(referer = url_referer))
        else:
            response = requests.get(url)
        file_name = get_filename_from_url(url)
        file_name = prepend_date_time_to_string(file_name)
        with open(os.path.join(upload_dir, file_name), 'wb') as file:
            file.write(response.content)
        return file_name
    except requests.exceptions.RequestException as e:
        return str(e)

def prepend_date_time_to_string(string):
    return time.strftime('%Y-%m-%d_%H-%M-%S_') + string

# From: http://flask.pocoo.org/docs/0.12/patterns/fileuploads/#a-gentle-introduction
# Sample: allowed_extensions = set(['png', 'jpg', 'jpeg', 'gif', 'svg'])
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# From: https://stackoverflow.com/questions/38987/how-to-merge-two-python-dictionaries-in-a-single-expression/26853961#26853961
# Given two dicts, merge them into a new dict as a shallow copy.
def merge_two_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z

# this is used for sql queries where direct input is required
# in sql statements, single quotes are escaped by doubling them up 
def escape_for_sql(string):
    return string.replace("'", "''")

def request_wants_json():
    best = request.accept_mimetypes.best_match(['text/html', 'application/json'])
    return best == 'application/json' and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']

def check_if_any_one_of_the_given_tags_exist(art, tags):
    for art_tag in art['tags']:
        for tag in tags:
            if art_tag['tag_name'] == tag:
                return True