import requests, re, json
from bs4 import BeautifulSoup

def deviant_art(art_url, username=None, password=None):

    html_source = requests.get(art_url).text
    soup = BeautifulSoup(html_source, "html.parser")

    art = {}

    art['title'] = soup.select('div.dev-title-container > h1 > a')[0].text

    if soup.select('img.dev-content-full'):
        art['image_url'] = soup.select('img.dev-content-full')[0].get('src')
    else: # this usually means the art we're requesting is marked as mature
        if username and password: # proceed to login if username and password have been passed
            with requests.Session() as session:
                html_reponse = session.get('https://www.deviantart.com/users/login').text
                soup = BeautifulSoup(html_reponse, "html.parser")

                payload = {
                    'username': username,
                    'password': password,
                    'validate_token': soup.find('input', {"name":"validate_token"})['value'],
                    'validate_key': soup.find('input', {"name":"validate_key"})['value']
                }

                session.post('https://www.deviantart.com/users/login', data=payload)

                html_reponse = session.get(art_url).text
                soup = BeautifulSoup(html_reponse, "html.parser")

                if soup.select('img.dev-content-full'): # if login succeeds
                    art['image_url'] = soup.select('img.dev-content-full')[0].get('src')
                else:
                    art['image_url'] = ''
        else:
            art['image_url'] = ''

    artist = soup.select('div.dev-title-container > h1 > small > span.username-with-symbol.u > a')[0]
    art['artist_name'] = artist.text
    art['artist_website'] = artist.get('href')
    art['source'] = art_url

    return art

def art_station(art_url):

    artstation_art_id = re.search(r"artwork\/([a-z,0-9,A-Z]*)", art_url).group(1)
    json_url = "https://www.artstation.com/projects/{}.json".format(artstation_art_id)
    art_data = requests.get(json_url).json()

    art = {}

    art['title'] = art_data['title']
    art['image_url'] = art_data['assets'][0]['image_url']
    art['artist_name'] = art_data['user']['full_name']
    art['artist_website'] = art_data['user']['permalink']
    art['source'] = art_url

    return art