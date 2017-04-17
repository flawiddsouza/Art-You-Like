import requests, re, json
from bs4 import BeautifulSoup

def deviant_art(art_url):

    html_source = requests.get(art_url).text
    soup = BeautifulSoup(html_source, "html.parser")

    art = {}

    art['title'] = soup.select('div.dev-title-container > h1 > a')[0].text
    art['image_url'] = soup.select('img.dev-content-full')[0].get('src')
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