#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handles exceptions while interacting with Selenium objects
"""
from random import randint
import time
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Union,
)

from loguru import logger
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import (
    By,
    WebElement,
)


class ChromeDriver(Chrome):
    """
    Initiates Chromedriver for Selenium
    Args for __init__:
        driver_path: path to Chromedriver
        timeout: int, seconds to wait until connection unsuccessful
        options: list, any extra options to add to chrome_options.add_argument()
    """

    chrome_default_options = [
        '--disable-extensions',
        '--mute-audio',
        '--disable-infobars',  # Get rid of "Chrome is being controlled by automated software" notification
        '--start-maximized',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--lang=en_US'
    ]

    def __init__(self, driver_path: str = '/usr/bin/chromedriver', timeout: float = 60,
                 options: List[str] = None, headless: bool = True):
        self.driver_path = driver_path

        # Add options to Chrome
        opt_list = options if options is not None else self.chrome_default_options
        chrome_options = Options()
        for option in opt_list:
            chrome_options.add_argument(option)

        if headless:
            chrome_options.add_argument('--headless')
        # Disable notifications
        prefs = {
            'profile.default_content_setting_values.notifications': 2,
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
        }
        chrome_options.add_experimental_option('prefs', prefs)
        # Apply options
        super(ChromeDriver, self).__init__(self.driver_path, chrome_options=chrome_options)
        # Set timeout for 1 minute to avoid multiple instances opening over time
        super(ChromeDriver, self).set_page_load_timeout(timeout)


class BrowserAction:
    """
    Performs action to Selenium-class webdriver
    Args for __init__:
        driver: Selenium-type driver class
    """
    # Predefined wait ranges, in seconds
    _slow_wait = [15, 30]
    _medium_wait = [5, 15]
    _fast_wait = [1, 8]
    REST_S = 2          # Standard seconds to rest between attempts
    STD_ATTEMPTS = 3    # Standard attempts to make before failing

    def __init__(self, driver_path: str = '/usr/bin/chromedriver',
                 timeout: float = 60, options: List[str] = None, headless: bool = True, parent_log: logger = None):
        self.driver = ChromeDriver(driver_path, timeout, options, headless)
        self.pid = self.driver.service.process.pid
        self.port = self.driver.service.port
        self.log = parent_log.bind(child_name=self.__class__.__name__)
        self.log.debug(f'Chromedriver started up with pid: {self.pid} receiving on port: {self.port}')

    def elem_by_xpath(self, val):
        return self.driver.find_element(by=By.XPATH, value=val)

    def elems_by_xpath(self, val):
        return self.driver.find_elements(by=By.XPATH, value=val)

    def _do_attempts(self, func: Callable, *args, sub_method: str = None, sub_method_input: str = None,
                     attempts: int = 3, rest_s: float = 2) -> Optional[Any]:
        """Attempts a certain method for n times before gracefully failing"""

        for i in range(0, attempts):
            if i > 0:
                # Sleep between attempts, but let a one-off attempt through without much delay
                time.sleep(rest_s)
            try:
                thing = func(*args)
                if sub_method is not None:
                    if sub_method_input is None:
                        getattr(thing, sub_method)()
                        break
                    else:
                        getattr(thing, sub_method)(sub_method_input)
                        break
                else:
                    return thing
            except Exception as e:
                self.log.error(f'Attempt {i + 1}: fail -- {e}')

    def tear_down(self):
        """Make sure the browser is closed on cleanup"""
        self.log.info('Shutting down browser.')
        self.driver.quit()

    def get(self, url: str):
        """
        Navigates browser to url
        Args:
            url: str, url to navigate to
        """
        self.log.debug(f'Loading url: {url}')
        self.driver.get(url)

    def click(self, xpath: str, attempts: int = STD_ATTEMPTS, rest_s: float = REST_S):
        """
        Clicks HTML element
        Args:
            xpath: str, xpath to element to click
            attempts: int, number of attempts to make before failing
            rest_s: int, number of seconds to rest between attempts
        """
        self._do_attempts(self.elem_by_xpath, xpath, sub_method='click', attempts=attempts, rest_s=rest_s)

    def clear(self, xpath: str, attempts: int = STD_ATTEMPTS, rest_s: float = REST_S):
        """
        Clears form element of text
        Args:
            xpath: str, xpath to form element
            attempts: int, number of attempts to make before failing
            rest_s: int, number of seconds to rest between attempts
        """
        self._do_attempts(self.elem_by_xpath, xpath, sub_method='clear', attempts=attempts, rest_s=rest_s)

    def enter(self, xpath: str, entry_text: str, attempts: int = STD_ATTEMPTS, rest_s: float = REST_S):
        """
        Enters text into form element
        Args:
            xpath: str, xpath to form
            entry_text: str, text to enter into form
            attempts: int, number of attempts to make before failing
            rest_s: int, number of seconds to rest between attempts
        """
        self._do_attempts(self.elem_by_xpath, xpath, sub_method='send_keys', sub_method_input=entry_text,
                          attempts=attempts, rest_s=rest_s)

    def elem_exists(self, xpath: str, attempts: int = 1, rest_s: float = REST_S) -> bool:
        """
        Determines if particular element exists
        Args:
            xpath: str, xpath to HTML element
            attempts: int, number of attempts to make before failing
            rest_s: int, number of seconds to rest between attempts
        Returns: True if exists
        """
        elem = self._do_attempts(self.elem_by_xpath, xpath, attempts=attempts, rest_s=rest_s)
        if elem is not None:
            return True
        return False

    def get_elem(self, xpath: str, single: bool = True, attempts: int = STD_ATTEMPTS, rest_s: float = REST_S) ->\
            Union[WebElement, List[WebElement]]:
        """
        Returns HTML elements as selenium objects
        Args:
            xpath: str, xpath of element to return
            single: boolean, True if returning only one element. default: True
            attempts: int, number of attempts to make before failing
            rest_s: int, number of seconds to rest between attempts
        Returns: HTML element(s) matching xpath text
        """
        if single:
            return self._do_attempts(self.elem_by_xpath, xpath, attempts=attempts, rest_s=rest_s)
        else:
            return self._do_attempts(self.elems_by_xpath, xpath, attempts=attempts, rest_s=rest_s)

    def get_text(self, xpath: str, single: bool = True, attempts: int = STD_ATTEMPTS, rest_s: float = REST_S) ->\
            Union[str, List[str]]:
        """
        Returns text in element(s)
        Args:
            xpath: str, xpath to element
            single: boolean, Whether to extract from single element or multiple. default = True
            attempts: int, number of attempts to make before failing
            rest_s: int, number of seconds to rest between attempts
        Returns: Text from inside element(s)
        """
        if single:
            elem = self._do_attempts(self.elem_by_xpath, xpath, attempts=attempts, rest_s=rest_s)
            if elem is not None:
                return elem.text
        else:
            elems = self._do_attempts(self.elems_by_xpath, xpath, attempts=attempts, rest_s=rest_s)
            text_list = []
            for e in elems:
                if e is not None:
                    text_list.append(e.text)
            return text_list

    def remove(self, xpath: str, single: bool = True, attempts: int = STD_ATTEMPTS, rest_s: float = REST_S):
        """
        Uses JavaScript commands to remove desired element
        Args:
            xpath: str, xpath to element
            single: boolean whether to apply to single element or multiple. default = True
            attempts: int, number of attempts to make before failing
            rest_s: int, number of seconds to rest between attempts
        """
        script = """
        var element = arguments[0];
        element.remove();
        """
        if single:
            elem = self._do_attempts(self.elem_by_xpath, xpath, attempts=attempts, rest_s=rest_s)
            if elem is not None:
                self.driver.execute_script(script, elem)
        else:
            elems = self._do_attempts(self.elems_by_xpath, xpath, attempts=attempts, rest_s=rest_s)
            for e in elems:
                if e is not None:
                    self.driver.execute_script(script, e)

    def add_style_to_elem(self, elem: WebElement, css_str: str):
        """Injects CSS into elem style"""
        js = f"arguments[0].setAttribute('style', '{css_str}');"
        self.driver.execute_script(js, elem)

    def click_by_id(self, elem_id: float):
        js = f'document.getElementById("{elem_id}").click();'
        self.driver.execute_script(js)

    def rand_wait(self, sleep_range_secs: List[int]):
        """
        Determines sleep time as random number between upper and lower limit,
            then sleeps for that given time. After sleep, moves randomly vertically and horizontally on page
            for up to four times
        Args:
            sleep_range_secs: list, min and max number of seconds to sleep
        """
        sleep_range_secs = sorted(sleep_range_secs)
        if len(sleep_range_secs) == 2:
            sleep_secs_lower, sleep_secs_higher = sleep_range_secs
        elif len(sleep_range_secs) > 2:
            sleep_secs_lower, sleep_secs_higher = sleep_range_secs[0], sleep_range_secs[-1]
        else:
            raise ValueError('Input for sleep range must be at least two items')
        sleeptime = randint(sleep_secs_lower, sleep_secs_higher)
        self.log.debug(f'Waiting {sleeptime}s')
        time.sleep(sleeptime)
        # after wait period, scroll through window randomly
        for i in range(4):
            r_x = randint(-20, 20)
            r_y = randint(150, 300)
            self.scroll_absolute(direction=f'{r_x},{r_y}')

    def fast_wait(self):
        self.rand_wait(self._fast_wait)

    def medium_wait(self):
        self.rand_wait(self._medium_wait)

    def slow_wait(self):
        self.rand_wait(self._slow_wait)

    def scroll_to_element(self, elem: WebElement, use_selenium_method: bool = True):
        """
        Scrolls to get element in view
        Args:
            elem: Selenium-class element
            use_selenium_method: bool, if True, uses built-in Selenium method of scrolling an element to view
                otherwise, uses Javascript (scrollIntoView)
        """
        if use_selenium_method:
            actions = ActionChains(self.driver)
            actions.move_to_element(elem).perform()
        else:
            scroll_center_script = """
                var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
                var elementTop = arguments[0].getBoundingClientRect().top;
                window.scrollBy(0, elementTop-(viewPortHeight/2));
            """
            self.driver.execute_script(scroll_center_script, elem)

    def scroll_absolute(self, direction: str = 'up'):
        """Scrolls all the way up/down or to specific x,y coordinates"""
        if direction == 'up':
            coords = '0, 0'
        elif direction == 'down':
            coords = '0, document.body.scrollHeight'
        else:
            if ',' in direction:
                coords = direction
            else:
                raise ValueError('Invalid parameters entered. Must be an x,y coordinate, or up/down command.')

        self.driver.execute_script(f'window.scrollTo({coords});')
