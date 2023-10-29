import argparse
import os
import re
import json
from time import sleep
from random import uniform

import pandas as pd
from selenium import webdriver
from selenium.webdriver import chrome, firefox
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys


class MapsCrawler:
    def __init__(self, args) -> None:
        self.headless_browser = True
        self.driver = ""
        self.current_path = os.getcwd() + "/"
        self.webdriver_path = self.current_path + "Web Driver" + "/"
        self.start=args.s
        self.end=args.e

    def check_driver(self):
        if self.driver:
            self.driver.quit()

    def load_firefox_driver(self):
        self.check_driver()

        profile = webdriver.FirefoxProfile()
        profile.set_preference('intl.accept_languages', 'en-GB, en')
        profile.set_preference('permissions.default.image', 2)
        profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
        options = firefox.options.Options()

        if self.headless_browser:
            options.headless = True
        
        options.accept_untrusted_certs = True
        self.driver = webdriver.Firefox(executable_path=self.webdriver_path + 'geckodriver', options=options,
                                        firefox_profile=profile)

    def pop_up(self):
        try:
            self.driver.find_element_by_css_selector('#L2AGLb').click()
        except Exception as e:
            pass
    
    def set_driver(self, query, method=0):
        self.driver.delete_all_cookies()

        if method == 0:
            # self.driver.get('https://www.google.com/maps')
            self.driver.get('https://www.google.com/search?sca_esv=577481235&tbs=lf:1,lf_ui:9&tbm=lcl&sxsrf=AM9HkKk6ncdRQExpSJ299yk-IFawWhDBhA:1698518539189&q=Restaurants&rflfq=1&num=10&sa=X&ved=2ahUKEwjqw7DRspmCAxX5HjQIHXpnCLUQjGp6BAggEAE&biw=910&bih=995&dpr=1.25#rlfi=hd:;si:;mv:[[47.6160165,-122.3367948],[47.610045299999996,-122.34715759999999]];tbs:lrf:!1m4!1u3!2m2!3m1!1e1!1m4!1u5!2m2!5m1!1sgcid_3american_1restaurant!1m4!1u5!2m2!5m1!1sgcid_3italian_1restaurant!1m4!1u2!2m2!2m1!1e1!1m4!1u1!2m2!1m1!1e1!1m4!1u1!2m2!1m1!1e2!1m4!1u22!2m2!21m1!1e1!2m1!1e2!2m1!1e5!2m1!1e1!2m1!1e3!3sIAEqAlVT,lf:1,lf_ui:9')

            self.pop_up()
        
        else:
            self.driver.delete_all_cookies()
            self.driver.get(self.base_url_t.format(query=query))
    
    def fetch_records(self):
        records = pd.read_excel('addresses.xlsx').to_dict('records')

        for ind, rec in enumerate(records, start=1):
            rec['index'] = ind
            zip_code = rec['addresses'].split('-')[-1].split(',')[-1].strip()
            rec['zipcode'] = f'{zip_code[:-3]}-{zip_code[-3:]}'

        return records
    
    def save_records(self, records):
        with open(f'Records_{self.start}_{self.end}.json', 'w') as f:
            json.dump(records, f)

    def reset_driver(self):
        self.check_driver()
        sleep(30)
        self.load_firefox_driver()
        self.set_driver(query="", method=0)

    def start_requests(self):
        self.load_firefox_driver()
        self.set_driver(query="", method=0)
        records = self.fetch_records()

        count = self.start
        save_clock = 0
        records_chunk = records[self.start:self.end]
        scrapped = []

        for rec in records_chunk:
            print(count, end=" ")
            try:
                rec.update(self.query_address(rec['addresses']))
            except Exception:
                self.save_records(scrapped)
                self.reset_driver()

            scrapped.append(rec)

            count += 1
            save_clock += 1

            if save_clock >= 50:
                save_clock = 0
                self.save_records(scrapped)
                self.reset_driver()

        self.save_records(scrapped)

    def enter_words(self, box, address):
        for c in [*address]:
            box.send_keys(c)
            sleep(0.1)

    def multiple_results(self):
        try:
            tile = self.driver.find_element(By.CSS_SELECTOR, ".hfpxzc")

            if tile:
                tile.click()
        except Exception:
            pass

    
    def get_coordinates_maps(self):
        for x in range(2000):
            results = re.findall("!3d(.*?)!4d(.*?)(?:\?|\!)", self.driver.current_url)

            if results:
                break

        print(results)

        if not results:
            return {}

        return {
                'latitude': results[0][0],
                'longitude': results[0][1],
                'maps_url': self.driver.current_url
                }

    def get_coordinates_search(self):
        results = ""

        for x in range(2000):
            try:
                results = self.driver.find_element(By.CSS_SELECTOR, ".rllt__mi")

                if results:
                    break
            except Exception:
                pass

        if not results:
            coord = {"latitude": "", "longitude": "", "maps_url": ""}
        
        else:
            coord =  {
                    'latitude': results.get_attribute("data-lat"),
                    'longitude': results.get_attribute("data-lng"),
                    'maps_url': self.driver.current_url
                    }
        
        print(f'{coord["latitude"]},{coord["longitude"]}')
        return coord
    
    def query_address(self, address):
        # search_box = self.driver.find_element(By.CSS_SELECTOR, "#searchboxinput")
        search_box = self.driver.find_element(By.CSS_SELECTOR, '[aria-label="Search"]')
        search_box.clear()
        self.enter_words(box=search_box, address=address)
        # self.driver.find_element(By.CSS_SELECTOR, "#searchbox-searchbutton").click()
        self.driver.find_element(By.CSS_SELECTOR, '[aria-label="Google Search"]').click()
        sleep(3)
        # self.multiple_results()
        # return self.get_coordinates_maps()
        return self.get_coordinates_search()



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", type=int, help="Enter start index of business", default=0)
    parser.add_argument("-e", type=int, help="Enter end index of business", default=1000)
    args = parser.parse_args()
    crawler = MapsCrawler(args)
    crawler.start_requests()
