from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import os
import requests, re, json

chrome_options = Options()
chrome_options.add_argument("--headless")
# chrome_options.add_argument("--window-size=1920x1080")
# disable loading of images - from: https://stackoverflow.com/a/31581387/4932305 [
prefs = { "profile.managed_default_content_settings.images" : 2 }
chrome_options.add_experimental_option("prefs", prefs)
# ]
bins_path = os.path.join(os.path.dirname(__file__), 'bins')
chrome_driver  = os.path.join(bins_path, 'chromedriver')

def deviant_art(art_url, username=None, password=None):

    driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=chrome_driver)

    driver.get(art_url)

    art = {}

    art['title'] = driver.find_element_by_class_name('title').text
    artist = driver.find_element_by_xpath("//a[@class='u regular username']")
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
                    driver.get(image_download_link) # since image_download_link is a redirect, we need to resolve it to get the direct link
                    art['image_url'] = driver.current_url
                except:
                    image_element = WebDriverWait(driver, 10).until(lambda driver: driver.find_element_by_class_name('dev-content-full'))
                    art['image_url'] = image_element.get_attribute('src')

            except Exception as e:
                print(e)
                art['image_url'] = ''

    driver.close()
    driver.quit()

    return art

def art_station(art_url):

    artstation_art_id = re.search(r"artwork\/([a-z,0-9,A-Z]*)", art_url).group(1)
    json_url = "https://www.artstation.com/projects/{}.json".format(artstation_art_id)
    art_data = requests.get(json_url).json()

    art = {}

    art['title'] = art_data['title']
    if art_data['assets'][0]['has_image']:
        art['image_url'] = art_data['assets'][0]['image_url']
    else:
         art['image_url'] = art_data['assets'][1]['image_url']
    art['artist_name'] = art_data['user']['full_name']
    art['artist_website'] = art_data['user']['permalink']
    art['source'] = art_url

    return art