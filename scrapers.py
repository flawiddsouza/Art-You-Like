from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import os
import requests, re, json
import msgpack
from bs4 import BeautifulSoup

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-logging")
# chrome_options.add_argument("--disable-gpu")
# disable loading of images - from: https://stackoverflow.com/a/31581387/4932305 [
prefs = { "profile.managed_default_content_settings.images" : 2 }
chrome_options.add_experimental_option("prefs", prefs)
# ]
bins_path = os.path.join(os.path.dirname(__file__), 'bins')
chrome_driver  = os.path.join(bins_path, 'chromedriver')

cookies_path = os.path.join(os.path.dirname(__file__), 'cookies')
deviantart_cookies = os.path.join(cookies_path, 'DeviantArt.msgpack')
pixiv_cookies = os.path.join(cookies_path, 'Pixiv.msgpack')

def deviant_art(art_url):

    driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=chrome_driver)

    driver.get("https://tvchecklist.com/404") # need to navigate to a page before setting a cookie :/
    try:
        with open(deviantart_cookies, 'rb') as file_to_be_read:
            cookies = msgpack.unpack(file_to_be_read, encoding='utf-8') # without the encoding everything is prefixed with a "b"
            for cookie in cookies:
                driver.add_cookie(cookie)
    except:
        pass

    driver.get(art_url)

    art = {}

    art['title'] = driver.find_element_by_class_name('title').text
    artist = driver.find_element_by_xpath("//*[@id='output']/div/div[3]/div[1]/div[2]/div/div[1]/h1/small/span[2]/a")
    art['artist_name'] = artist.text
    art['artist_website'] = artist.get_attribute('href')
    art['source'] = art_url

    try:
        image_download_link = driver.find_element_by_xpath('//a[contains(@class, "dev-page-download")]').get_attribute('href')
        driver.get(image_download_link) # since image_download_link is a redirect, we need to resolve it to get the direct link
        art['image_url'] = driver.current_url
    except:
        try:
            art['image_url'] = driver.find_element_by_class_name('dev-content-full').get_attribute('src')
        except: # this usually means the art we're requesting is marked as mature
            try: # part from https://github.com/Romitas/DeviantArtScraper/blob/master/deviant/spiders/deviant_spider.py
                month = driver.find_element_by_id('month')
                day   = driver.find_element_by_id('day')
                year  = driver.find_element_by_id('year')

                agree   = driver.find_element_by_id('agree_tos')
                submit  = driver.find_element_by_xpath('//input[contains(@class, "submitbutton")]')

                month.send_keys('10')
                day.send_keys('21')
                year.send_keys('1990')

                agree.click()
                submit.click()

                try:
                    # the only WebDriverWait example that actually worked: https://stackoverflow.com/a/16927552/4932305
                    image_download_link = WebDriverWait(driver, 10).until(lambda driver: driver.find_element_by_xpath('//a[contains(@class, "dev-page-download")]').get_attribute('href'))
                    with open(deviantart_cookies, 'wb') as file_to_write_to:
                        msgpack.pack(driver.get_cookies(), file_to_write_to)
                    driver.get(image_download_link) # since image_download_link is a redirect, we need to resolve it to get the direct link
                    art['image_url'] = driver.current_url
                except:
                    image_element = WebDriverWait(driver, 10).until(lambda driver: driver.find_element_by_class_name('dev-content-full'))
                    with open(deviantart_cookies, 'wb') as file_to_write_to:
                        msgpack.pack(driver.get_cookies(), file_to_write_to)
                    art['image_url'] = image_element.get_attribute('src')

            except Exception as e:
                print(e)
                art['image_url'] = ''

    driver.close()
    driver.quit()

    return art

def art_station(art_url, multiple=False):

    artstation_art_id = re.search(r"artwork\/([a-z,0-9,A-Z]*)", art_url).group(1)
    json_url = "https://www.artstation.com/projects/{}.json".format(artstation_art_id)
    art_data = requests.get(json_url).json()

    art = {}

    art['title'] = art_data['title']
    if not multiple:
        if art_data['assets'][0]['has_image']:
            art['image_url'] = art_data['assets'][0]['image_url']
        else:
             art['image_url'] = art_data['assets'][1]['image_url']
    else:
        art['image_url'] = []
        for art_data_asset in art_data['assets']:
            if art_data_asset['has_image'] and not art_data_asset['has_embedded_player']:
                art['image_url'].append(art_data_asset['image_url'])
    art['artist_name'] = art_data['user']['full_name']
    art['artist_website'] = art_data['user']['permalink']
    art['source'] = art_url

    return art

def pixiv(art_url, username, password):

    driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=chrome_driver)

    driver.get('https://tvchecklist.com/404') # need to navigate to a page before setting a cookie :/
    try:
        with open(pixiv_cookies, 'rb') as file_to_be_read:
            cookies = msgpack.unpack(file_to_be_read, encoding='utf-8') # without the encoding everything is prefixed with a "b"
            for cookie in cookies:
                driver.add_cookie(cookie)
    except:
        pass

    driver.get(art_url)

    art = {}

    try: # check if the user not logged in - if not, then log in
        driver.find_element_by_xpath('//a[contains(@class, "ui-button _login")]').click()
        driver.find_element_by_xpath('//*[@id="LoginComponent"]/form/div[1]/div[1]/input').send_keys(username)
        driver.find_element_by_xpath('//*[@id="LoginComponent"]/form/div[1]/div[2]/input').send_keys(password)
        driver.find_element_by_xpath('//*[@id="LoginComponent"]/form/button').click()
        with open(pixiv_cookies, 'wb') as file_to_write_to:
            msgpack.pack(driver.get_cookies(), file_to_write_to)
    except Exception as e: # this means the user is logged in
        # print(e)
        pass

    try:
        art['title'] = driver.find_elements_by_class_name('title')[1].text
        artist = driver.find_element_by_xpath('//a[@class="user-name"]')
        art['artist_name'] = artist.text
        art['artist_website'] = artist.get_attribute('href')
        art['source'] = art_url
        art['image_url'] = driver.find_element_by_xpath('//img[@class="original-image"]').get_attribute('data-src')
    except Exception as e:
        print(e)

    driver.close()
    driver.quit()

    return art

def tumblr(art_url):

    html_doc = requests.get(art_url).text

    soup = BeautifulSoup(html_doc, 'html.parser')

    art = {}

    art['title'] = soup.find('meta',  property='og:title')['content']
    art['artist_name'] = soup.find('figcaption').text
    art['artist_website'] = re.search('https:\/\/.*\.tumblr\.com', art_url).group(0)
    art['source'] = art_url
    art['image_url'] = soup.find('meta',  property='og:image')['content']

    return art

def instagram(art_url):

    html_doc = requests.get(art_url).text

    soup = BeautifulSoup(html_doc, 'html.parser')

    art = {}

    json_data = soup.find_all('script')[2].text
    json_data = json_data.replace('window._sharedData = ', '').replace(';', '')
    json_data = json.loads(json_data)
    art_info = json_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']
    art['title'] = art_info['edge_media_to_caption']['edges'][0]['node']['text']
    art['title'] = re.sub('(\S*#(?:\[[^\]]+\]|\S+))', '', art['title']).strip() # strip all hash tags
    artist = art_info['owner']
    art['artist_name'] = artist['full_name']
    art['artist_website'] = 'http://www.instagram.com/' + artist['username'] + '/'
    art['source'] = art_url
    art['image_url'] = soup.find('meta',  property='og:image')['content']

    return art