import urllib.request as urllib
from bs4 import BeautifulSoup

def deviant_art(art_url):

    with urllib.urlopen(art_url) as html_source:

        html_source = html_source.read()
        soup = BeautifulSoup(html_source, "html.parser")

        art = {}

        art['title'] = soup.select('div.dev-title-container > h1 > a')[0].text
        art['image_url'] = soup.select('img.dev-content-full')[0].get('src')
        artist = soup.select('div.dev-title-container > h1 > small > span.username-with-symbol.u > a')[0]
        art['artist_name'] = artist.text
        art['artist_website'] = artist.get('href')
        art['source'] = art_url

        return art