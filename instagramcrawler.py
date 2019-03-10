# encoding=utf8  
from __future__ import division
import sys  

reload(sys)  
sys.setdefaultencoding('utf8')
import urllib

import argparse
import codecs
from collections import defaultdict
import json
import os
import re
import sys
import time
import re
try:
    from urlparse import urljoin
    from urllib import urlretrieve
except ImportError:
    from urllib.parse import urljoin
    from urllib.request import urlretrieve

import requests
import selenium
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# HOST
HOST = 'http://www.instagram.com'

# SELENIUM CSS SELECTOR
CSS_LOAD_MORE = "a._1cr2e._epyes"
CSS_RIGHT_ARROW = "a[class='_de018 coreSpriteRightPaginationArrow']"
FIREFOX_FIRST_POST_PATH = "//div[contains(@class, '_8mlbc _vbtk2 _t5r8b')]"
TIME_TO_CAPTION_PATH = "../../../div/ul/li/span"

# FOLLOWERS/FOLLOWING RELATED
CSS_EXPLORE = "a[href='/explore/']"
CSS_LOGIN = "a[href='/accounts/login/']"
CSS_FOLLOWERS = "a[href='/{}/followers/']"
CSS_FOLLOWING = "a[href='/{}/following/']"
FOLLOWER_PATH = "//div[contains(text(), 'Followers')]"
FOLLOWING_PATH = "//div[contains(text(), 'Following')]"

# JAVASCRIPT COMMANDS
SCROLL_UP = "window.scrollTo(0, 0);"
SCROLL_DOWN = "window.scrollTo(0, document.body.scrollHeight);"

class url_change(object):
    """
        Used for caption scraping
    """
    def __init__(self, prev_url):
        self.prev_url = prev_url

    def __call__(self, driver):
        return self.prev_url != driver.current_url

class InstagramCrawler(object):
    """
        Crawler class
    """
    def __init__(self, headless=True, firefox_path=None):
        if headless:
            print("headless mode on")
            self._driver = webdriver.PhantomJS()
        else:
            # credit to https://github.com/SeleniumHQ/selenium/issues/3884#issuecomment-296990844
            binary = FirefoxBinary(firefox_path)
            self._driver = webdriver.Firefox(firefox_binary=binary)

        self._driver.implicitly_wait(10)
        self.data = defaultdict(list)

    def login(self, authentication=None):
        """
            authentication: path to authentication json file
        """
        self._driver.get(urljoin(HOST, "accounts/login/"))

        if authentication:
            print("Username and password loaded from {}".format(authentication))
            with open(authentication, 'r') as fin:
                auth_dict = json.loads(fin.read())
            # Input username
            username_input = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located((By.NAME, 'username'))
            )
            username_input.send_keys(auth_dict['username'])
            # Input password
            password_input = WebDriverWait(self._driver, 5).until(
                EC.presence_of_element_located((By.NAME, 'password'))
            )
            password_input.send_keys(auth_dict['password'])
            # Submit
            password_input.submit()
        else:
            print("Type your username and password by hand to login!")
            print("You have a minute to do so!")

        print("")
        WebDriverWait(self._driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CSS_EXPLORE))
        )

    def quit(self):
        self._driver.quit()

    def crawl(self, dir_prefix, query, crawl_type, number, caption, authentication):
        print("dir_prefix: {}, query: {}, crawl_type: {}, number: {}, caption: {}, authentication: {}"
              .format(dir_prefix, query, crawl_type, number, caption, authentication))

        if crawl_type == "photos":
            # Browse target page
            self.browse_target_page(query)
            # Scroll down until target number photos is reached
            self.scroll_to_num_of_posts(number, query)
            # Scrape photo links
            #self.scrape_photo_links(number, is_hashtag=query.startswith("#"))
            # Scrape captions if specified
            if caption is True:
                self.click_and_scrape_captions(number)

        elif crawl_type in ["followers", "following"]:
            # Need to login first before crawling followers/following
            print("You will need to login to crawl {}".format(crawl_type))
            self.login(authentication)

            # Then browse target page
            assert not query.startswith(
                '#'), "Hashtag does not have followers/following!"
            self.browse_target_page(query)
            # Scrape captions
            self.scrape_followers_or_following(crawl_type, query, number)

        elif crawl_type == 'profile_img':
            self.browse_target_page(query)
            self.profile_img(crawl_type, query, number)
        
        elif crawl_type == 'page_id':
            relative_url = urljoin(HOST, "p/"+query+"/")

            target_url = urljoin(HOST, relative_url)

            self._driver.get(target_url)

            element_id = self._driver.find_element_by_xpath('//a[@class="FPmhX notranslate nJAzx"]')

            title = element_id.get_attribute('title')


            with open('./data/IDs/ids.txt', 'a') as myfile:
                myfile.write(title + "\n")

            time.sleep(1.0)

            self.quit()

        elif crawl_type == 'get_page_id':
            for i in range(0, len(os.listdir('./data/'))):
                print(os.listdir('./data/')[i])
                for j in range(0, len(os.listdir('./data/'+os.listdir('./data/')[i]))):
                    print(os.listdir('./data/'+os.listdir('./data/')[i])[j])
            self.quit()
        else:
            print("Unknown crawl type: {}".format(crawl_type))
            self.quit()
            return
        # Save to directory
            print("Saving...")
            self.download_and_save(dir_prefix, query, crawl_type)

            # Quit driver
            print("Quitting driver...")
            self.quit()

    def browse_target_page(self, query):
        # Browse Hashtags
        if query.startswith('#') or '#' in query:
            relative_url = urljoin('explore/tags/', query.strip('#'))
        else:  # Browse user page
            relative_url = query

        target_url = urljoin(HOST, relative_url)

        self._driver.get(target_url)

    def scroll_to_num_of_posts(self, number, query):

        num_of_posts_str = self._driver.find_element_by_xpath('//span[@class="g47SY "]').text

        if ',' in num_of_posts_str:

            num_of_posts_str = re.sub(",", "", num_of_posts_str)
            num_of_posts = int(num_of_posts_str)

        else:

            num_of_posts = int(num_of_posts_str)

        number = number if number < num_of_posts else num_of_posts
        print("posts: {}, number of scrolls: {}".format(num_of_posts, number))
        dir_path = './data/'+str(query)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        num_to_scroll = number
        finallist=[]
        for _ in range(num_of_posts):
            page1 = self._driver.find_elements_by_xpath('//div[@class="v1Nh3 kIKUG  _bz0w"]/a')
            page2 = self._driver.find_elements_by_xpath('//div[@class="v1Nh3 kIKUG  _bz0w"]/a/div/div/img')
            for p in range(0, len(page1)):
                name = page1[p].get_attribute('href')[28:39]
                if '/' in name:
                    name = re.sub("/", "", name)
                if name not in finallist:
                    print('##########', len(finallist))
                    if len(finallist)+1 == num_of_posts:
                        self.quit()
                    else:
                        finallist.append(name)

                        img_name = './data/'+query.decode().encode('utf-8')+"/"+name+'.jpg'

                        urllib.urlretrieve(page2[p].get_attribute('src'), img_name)

            self._driver.execute_script(SCROLL_DOWN)
            
            time.sleep(0.3)
        self.quit()
    def click_and_scrape_captions(self, number):
        print("Scraping captions...")
        captions = []

        for post_num in range(number):
            sys.stdout.write("\033[F")
            print("Scraping captions {} / {}".format(post_num+1,number))
            if post_num == 0:  # Click on the first post
                # Chrome
                # self._driver.find_element_by_class_name('_ovg3g').click()
                self._driver.find_element_by_xpath(
                    FIREFOX_FIRST_POST_PATH).click()

                if number != 1:  #
                    WebDriverWait(self._driver, 5).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, CSS_RIGHT_ARROW)
                        )
                    )

            elif number != 1:  # Click Right Arrow to move to next post
                url_before = self._driver.current_url
                self._driver.find_element_by_css_selector(
                    CSS_RIGHT_ARROW).click()

                # Wait until the page has loaded
                try:
                    WebDriverWait(self._driver, 10).until(
                        url_change(url_before))
                except TimeoutException:
                    print("Time out in caption scraping at number {}".format(post_num))
                    break

            # Parse caption
            try:
                time_element = WebDriverWait(self._driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "time"))
                )
                caption = time_element.find_element_by_xpath(
                    TIME_TO_CAPTION_PATH).text
            except NoSuchElementException:  # Forbidden
                print("Caption not found in the {} photo".format(post_num))
                caption = ""

            captions.append(caption)

        self.data['captions'] = captions
        
    def profile_img(self, crawl_type, query, number):
        try:
            img = self._driver.find_element_by_xpath('//img[@class="_6q-tv"]')
        except:
            img = self._driver.find_element_by_xpath('//button[@class="IalUJ "]/img')
        src = img.get_attribute('src')
        # download the image
        img_name = './data/'+query+'.jpg'
        urllib.urlretrieve(src, img_name)

    def scrape_followers_or_following(self, crawl_type, query, number):
        print("Scraping {}...".format(crawl_type))
        if crawl_type == "followers":
            FOLLOW_ELE = CSS_FOLLOWERS
            FOLLOW_PATH = FOLLOWER_PATH
        elif crawl_type == "following":
            FOLLOW_ELE = CSS_FOLLOWING
            FOLLOW_PATH = FOLLOWING_PATH

        # Locate follow list
        follow_ele = WebDriverWait(self._driver, 5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, FOLLOW_ELE.format(query)))
        )

        # when no number defined, check the total items
        if number is 0:
            number = int(filter(str.isdigit, str(follow_ele.text)))
            print("getting all " + str(number) + " items")

        # open desired list
        follow_ele.click()

        title_ele = WebDriverWait(self._driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, FOLLOW_PATH))
        )

        
        follow_items = []
        element = self._driver.find_element_by_xpath('//div[@class="isgrP"]')
        n = 50
        followiingcount= self._driver.find_elements_by_xpath('//a[@class="-nal3 "]/span')[1].text

        for _ in range(number):
            print(_)
            time.sleep(0.1)
            
            self._driver.execute_script("arguments[0].scrollTop = " + str(n), element)
            n = n + 50
            

        List = title_ele.find_elements_by_xpath('//a[@class="FPmhX notranslate _0imsa "]')

        for ele in range(0,len(List)):
            follow_items.append(List[ele].get_attribute("title"))

        self.data[crawl_type] = follow_items

    def download_and_save(self, dir_prefix, query, crawl_type):

        # Check if is hashtag
        dir_name = query.lstrip(
            '#') + '.hashtag' if query.startswith('#') else query

        dir_path = os.path.join(dir_prefix, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        print("Saving to directory: {}".format(dir_path))

        # Save Photos
        for idx, photo_link in enumerate(self.data['photo_links'], 0):
            sys.stdout.write("\033[F")
            print("Downloading {} images to ".format(idx + 1))
            # Filename
            _, ext = os.path.splitext(photo_link)
            filename = str(idx) + ext
            filepath = os.path.join(dir_path, filename)
            # Send image request
            
            urlretrieve(photo_link, filepath)
        #try:
        #   title_name = self._driver.find_element_by_xpath('//div[@class="-vDIg"]/h1').text
        #    bio = self._driver.find_element_by_xpath('//div[@class="-vDIg"]/span').text
        #   print(20*'*', bio, title_name)
            
        # Save Captions
        for idx, caption in enumerate(self.data['captions'], 0):

            filename = str(idx) + '.txt'
            filepath = os.path.join(dir_path, filename)

            with codecs.open(filepath, 'w', encoding='utf-8') as fout:
                fout.write(caption + '\n')

        # Save followers/following
        filename = crawl_type + '.txt'
        filepath = os.path.join(dir_path, filename)
        if len(self.data[crawl_type]):
            with codecs.open(filepath, 'w', encoding='utf-8') as fout:
                for fol in self.data[crawl_type]:
                    fout.write(fol + '\n')


def main():
    #   Arguments  #
    parser = argparse.ArgumentParser(description='Instagram Crawler')
    parser.add_argument('-d', '--dir_prefix', type=str,
                        default='./data/', help='directory to save results')
    parser.add_argument('-q', '--query', type=str, default='instagram',
                        help="target to crawl, add '#' for hashtags")
    parser.add_argument('-t', '--crawl_type', type=str,
                        default='photos', help="Options: 'photos' | 'followers' | 'following'")
    parser.add_argument('-n', '--number', type=int, default=0,
                        help='Number of posts to download: integer')
    parser.add_argument('-c', '--caption', action='store_true',
                        help='Add this flag to download caption when downloading photos')
    parser.add_argument('-l', '--headless', action='store_true',
                        help='If set, will use PhantomJS driver to run script as headless')
    parser.add_argument('-a', '--authentication', type=str, default=None,
                        help='path to authentication json file')
    parser.add_argument('-f', '--firefox_path', type=str, default=None,
                        help='path to Firefox installation')
    args = parser.parse_args()
    #  End Argparse #

    crawler = InstagramCrawler(headless=args.headless, firefox_path=args.firefox_path)
    crawler.crawl(dir_prefix=args.dir_prefix,
                  query=args.query,
                  crawl_type=args.crawl_type,
                  number=args.number,
                  caption=args.caption,
                  authentication=args.authentication)


if __name__ == "__main__":
    main()
