'''
This file implements some useful routines:
-> setup_driver:
    Setups and returns a Firefox selenium webdriver in headless mode
-> wait_until:
    Stops execution of the program until a given hour, minute and second have been reached
-> sign_in:
    Signs into the booking webpage and accepts cookies
-> get_booking_page:
    Opens the booking webpage for a given venue and day
-> is_slot_available:
    From a venue booking webpage checks availability for a given slot across all
    courts
-> book_slot:
    From a venue booking webpage tries to book a given slot (for a given court
    at a certain time)
-> book:
    This is the main function. It tries to book a slot in the selected venue for
    the day and times(s) specified, by iterating over all courts and over all
    specified times.
'''
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options
import sys
import time

from constants import TAG, ATTR

# envs
load_dotenv()

WAITING_TIME = 2
logger = logging.getLogger(__name__)
s_handler = logging.StreamHandler()
s_handler.setLevel(logging.DEBUG)
logger.addHandler(s_handler)

def setup_driver():
    '''
    This function sets up and returns a Firefox selenium webdriver in headless mode
    '''
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver.maximize_window()
    return driver


def wait_until(hour=20, minute=0, second=0):
    '''
    This function stops execution until the hour, minute and second are reached
    Hour, minute and second default to 20.00.00pm, which is when the booking page
    for the following week opens
    '''
    if (hour < 0) or (hour > 23):
        hour = 20
    if (minute < 0) or (minute > 59):
        minute = 0
    if (second < 0) or (second > 59):
        second = 0

    now = datetime.now()
    trigger = datetime(now.year, now.month, now.day, hour, minute, second, 0)
    pre_trigger = trigger - timedelta(0, 1)
    while True:
        if datetime.now() >= trigger:
            break
        if datetime.now() < pre_trigger:
            time.sleep(1)
        else:
            pass


def sign_in(driver, username, password, poll_frequency=0.01):
    """
    This function signs into the booking website by providing email and password.
    It also accepts cookies in order to remove the banner in the following pages
    (not doing this may create some problems when trying to click on other buttons
    later on).
    """
    # e-mail and password
    WebDriverWait(driver, WAITING_TIME*2, poll_frequency).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@aria-labelledby='153:0-label']"))).send_keys(username)
    WebDriverWait(driver, WAITING_TIME*2, poll_frequency).until(
        EC.element_to_be_clickable((By.XPATH, "//input[@class='slds-input']"))).send_keys(password)

    # login
    WebDriverWait(driver, WAITING_TIME*2, poll_frequency).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@title="Log in"]'))).click()

    # accept cookies
    try:
        query = "a[class='cb-enable']"
        WebDriverWait(driver, WAITING_TIME * 2, poll_frequency).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, query))
        ).click()
    except:
        pass
    finally:
        # sleep 1 second - otherwise next steps may fail
        time.sleep(1)


def get_booking_page(driver, venue_url, day):
    """
    This function opens the correct booking page for a given venue and day
    Arguments:
    -driver: an instance of selenium webdriver
    -venue_url: a string with the root of the url of the venue booking pages
    -day: a string in the format 'YYYY-MM-DD'
    """
    driver.get(venue_url + f"#?date={day}&role=guest")


def is_slot_available(
    driver, start_time, day, court_ids, full_hour_only=False,
    poll_frequency=0.01, verbose=0
):
    """
    This function assumes that we are in a booking page already, and checks if a
    given slot is available for booking, by checking availability for all courts
    in the venue.

    Returns:
    -When a suitable slot is found, the associated court_id is returned.
    -If no suitable slots are found, it returns None.

    Arguments:
    -driver: an instance of selenium webdriver
    -start_time: in minutes - e.g. 8.00 am is 480, 8.30 am is 510, etc.
    -day: a string in the format 'YYYY-MM-DD'
    -court_ids: dictionary.
            keys: court label (e.g. court_1, court_2)
            value: string, the IDs of each court. These differ from each venue
    -full_hour_only: bool, if True only looks at full hour availability, otherwise
                    also looks at availability for 30 mins only.
                    Defaults to False.
    -poll_frequency: passed to WebDriverWait, regulates the frequency (in seconds)
                    in which the action is repeated.
                    Defaults to 0.01.
    -verbose: regulates how many information are printed. If '1', prints detailed
            information, otherwise doesn't print anything.
            Defaults to 0.
    """

    def _check_slot(start_time, court, court_id):
        query = f"{TAG}[{ATTR}='booking-{court_id}|{day}|{start_time}']"
        slot = f"{day} | {int(start_time/60)}:{start_time%60} in {court}"
        try:
            if verbose == 1:
                logger.info(f"Looking for slot: {slot}")
            btn = WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, query))
            )
            if btn.get_attribute("class") == "book-interval not-booked":
                return True
            else:
                return False
        except:
            if verbose == 1:
                logger.info(f"Slot not available: {slot}")
            return False

    for court in court_ids:
        if not _check_slot(start_time, court, court_ids[court]):
            continue
        if not full_hour_only:
            return court_ids[court]
        # if full_hour_only
        if not _check_slot(start_time+30, court, court_ids[court]):
            continue
        return court_ids[court]
    # if no slot was available in any court
    return None

def book_slot(
    driver, start_time, day, court_id, username, poll_frequency=0.01, verbose=0
):
    """ This function books the actual slot. The booking is done in 3 main steps:
        1. Find the available court(s) to book and click (+ accepting cookies)
        2. Sign in using username and password
        3. Make the payment and complete the booking
    """

    end_time = start_time + 60
    end_time_alt = start_time + 30
    end_time_repr = f"{end_time//60:02}:{end_time%60:02}"
    end_time_alt_repr = f"{end_time_alt//60:02}:{end_time_alt%60:02}"

    # try to click on the slot button
    slot = f"{day} | {int(start_time/60)}:{start_time%60}"

    # accept cookies
    try:
        driver.find_element(
            By.XPATH,
            '//button['
            '@class=" osano-cm-accept-all osano-cm-buttons__button osano-cm-button osano-cm-button--type_accept "]'
        ).click()
    except:
        pass
    finally:
        # sleep 1 second - otherwise next steps may fail
        time.sleep(1)

    try:
        if verbose == 1:
            print(f"Trying to book slot: {slot}")
        found = False
        query = f"{TAG}[{ATTR}='booking-{court_id}|{day}|{start_time}']"
        btn = WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, query))
        )
        if btn.get_attribute("class") == "book-interval not-booked":
            btn.click()
            found = True
    except:
        if verbose == 1:
            print(
                f"Failed to click on button for slot: {slot}")
        return -1

    # return 0 if slot button cannot be clicked (i.e. slot not available)
    if not found:
        if verbose == 1:
            print(f"There's no button for slot: {slot}")
        return 0

    # click on dropdown menu int order to select end_time of slot
    try:
        if verbose == 1:
            print(
                f"Clicking on end_time dropdown for slot: {slot}")
        query = "span[class='select2-selection__rendered']"
        btn = WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, query))
        )
        btn.click()
    except:
        if verbose == 1:
            print(
                f"Failed to click on end_time dropdown for slot: {slot}")
        return -1

    # click on end_time for slot
    try:
        if verbose == 1:
            print(f"Selecting end_time for slot: {slot}")
        full_slot = False
        lst = WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
            EC.presence_of_element_located((By.ID, "select2-booking-duration-results"))
        )
        items = lst.find_elements_by_tag_name("li")
        # first try 1 full hour
        for btn in items:
            if end_time_repr in btn.text:
                full_slot = True
                btn.click()
        # if not available, go for half hour
        if not full_slot:
            if verbose == 1:
                print(
                    f"Full hour not available for slot: {slot}")
            for btn in items:
                if end_time_alt_repr in btn.text:
                    btn.click()
    except:
        if verbose == 1:
            print(
                f"Failed to select end_time for slot: {slot}")
        return -1

    # continue booking
    WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
        EC.element_to_be_clickable((By.ID, 'submit-booking'))).click()

    # sign in using username and password
    WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@class="cs-btn primary med fw"]'))).click()
    try:
        sign_in(driver, os.getenv('USERNAME'), os.getenv('PASSWORD'))
        # sign_in(driver, username, keyring.get_password("LTA", username))
        if verbose == 1:
            print(f"Logged in {os.getenv('USERNAME')} successfully!")
        try:
            e = driver.find_element_by_xpath("//div[@id='error']//label[@class='slds-form-element_label']").text
            print(f"ERROR: {e}")
        except:
            pass
    except Exception as e:
        return e

    # Confirm
    WebDriverWait(driver, WAITING_TIME*2, poll_frequency).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@id="paynow"]'))).click()

    # payments handler
    # This requires a switch to iframe, and the nodes to complete the bank details are dynamically generated
    header = driver.find_element_by_xpath("//div[@class='cs-overlay ']")
    children_names = [x.get_attribute("name") for x in header.find_elements_by_xpath(".//*")]
    iframe_names = [x for x in children_names if x is not None]
    iframe_names = [x for x in iframe_names if '__private' in x]

    try:
        if verbose == 1:
            print(f"CARD Number added")
        iframe = WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
            EC.element_to_be_clickable((By.XPATH, f"//iframe[@name='{iframe_names[0]}']"))
        )
        driver.switch_to.frame(iframe)
        WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@class='InputElement is-empty Input Input--empty']")))\
            .send_keys(
                os.getenv('CARD_NUMBER')
        )

        driver.switch_to.default_content()
    except Exception as e:
        print(e)

    try:
        if verbose == 1:
            print(f"CARD Expiry date added")
        iframe = WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
            EC.element_to_be_clickable((By.XPATH, f"//iframe[@name='{iframe_names[1]}']"))
        )
        driver.switch_to.frame(iframe)
        WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@class='InputElement is-empty Input Input--empty']")))\
            .send_keys(
                os.getenv('CARD_EXPIRY_DATE')
        )
        driver.switch_to.default_content()
    except Exception as e:
        print(e)

    try:
        if verbose == 1:
            print(f"CARD CVC date added")
        iframe = WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
            EC.element_to_be_clickable((By.XPATH, f"//iframe[@name='{iframe_names[2]}']"))
        )
        driver.switch_to.frame(iframe)
        WebDriverWait(driver, WAITING_TIME, poll_frequency).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@class='InputElement is-empty Input Input--empty']")))\
            .send_keys(
                os.getenv('CARD_CVC')
        )
        driver.switch_to.default_content()
    except Exception as e:
        print(e)

    # make payment
    WebDriverWait(driver, WAITING_TIME*2, poll_frequency).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@id="cs-stripe-elements-submit-button"]'))).click()
    time.sleep(10)

    # add error handling for failed payments
    try:
        e = driver.find_element_by_xpath("//div[@class='cs-overlay ']//span[@class='error']").text
        print(f"PAYMENT ERROR: {e}")
    except:
        pass

    return 1

def book(driver, venue_url, court_ids, day, times,
         wait=None, full_hour_only=False, verbose=0):
    '''
    This function tries to book a slot in the selected venue for the day and
    times(s) specified, by iterating over all courts and over all specified times.
    Once a booking is successful, the function exits.

    Parameters:
    - driver: an instance of selenium webdriver
    - venue_url: string, url of the venue main booking page
    - login_details: tuple or list, with email in position 0 and password in position 1
    -court_ids: dictionary.
            keys: court label (e.g. court_1, court_2)
            value: string, the IDs of each court. These differ from each venue
    -day: a string in the format 'YYYY-MM-DD'
    -times: a list with the times we want to try and book for, expressed as
            strings ('hour:minute')
    -wait: either None (then the function will execute immediately) or a
          tuple/list in the form (hour, minute, second). In this case, the scrip
          will first login into the booking page and will then stop execution
          until the time threshold has been passed. Useful to book 1 week in
          advance as the booking page will open at 20pm (in which case, the value
          should be (20, 0, 0)).
    -full_hour_only: boolean, if True it will book a slot only if 1 full hour is
                    available, if False it will also book any 30mins slot it can
                    find
    -verbose: either 0 or 1. If 1, it will print some information on the booking
            progress.
    '''

    counter = 0
    if wait is not None:
        wait_until(wait[0], wait[1], wait[2])
    get_booking_page(driver, venue_url, day)
    for t in times:
        h, m = t.split(':')
        start_time = int(h) * 60 + int(m)
        court_id = is_slot_available(
            driver, start_time, day, court_ids, full_hour_only=False,
            verbose=verbose)
        if court_id is None:
            pass
        else:
            is_booked = book_slot(driver, start_time, day, court_id, os.getenv('USERNAME'),
                                  verbose=verbose)
            if is_booked == 1:
                counter += 1
            # get_booking_page(driver, venue_url, day)

    return counter
