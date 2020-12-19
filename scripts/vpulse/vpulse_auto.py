#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from datetime import datetime as dtt
from kavalkilu import LogWithInflux, Keys, NetTools, Hosts, HOME_SERVER_HOSTNAME
from servertools import BrowserAction, SlackComm


ip = NetTools().get_ip()
debug = Hosts().get_ip_from_host(HOME_SERVER_HOSTNAME) != ip
logg = LogWithInflux('vpulse_auto')

# TODO
# build out a table of when monthly, weekly things were last done.
# Handle weekly tasks either based on DOW or recorded table with date_last_done and freq columns

# Get credentials
creds = Keys().get_key('vpulse_creds')


def message_channel_and_log(msg):
    slack_comm.send_message(notify_channel, msg)
    if debug:
        logg.debug(msg)


def get_vpoints():
    """Collects amount of points currently available"""
    points_script = "return document.getElementById('progress-bar-menu-points-total-value')"
    points = ba.driver.execute_script(points_script).get_attribute('textContent').strip()

    if points.isdigit():
        return int(points)
    return 0


def get_available_rewards():
    """Determines if any rewards are available"""
    avail_rewards_script = "return document.getElementsByClassName('rewards-total-value')[0];"
    avail_rewards = ba.driver.execute_script(avail_rewards_script).get_attribute('textContent').strip()

    if avail_rewards != '$ 0':
        return avail_rewards
    return None


def popup_closer(xpath):
    """Attempts to close a popup"""
    logg.debug('Positioning to close popup')
    ba.scroll_absolute()
    ba.fast_wait()
    ba.click(xpath)
    logg.debug('Popup closing procedure complete.')


def initial_popup_closer():
    """Closes the initial popup that shows up"""
    popup_closer('//div[@id="trophy-modal-close-btn"]')


def daily_cards():
    """Handles the daily cards section"""
    ba.scroll_absolute()
    # Attempt to get make the cards section active
    card_btn = ba.get_elem('//div[@class="home-cards-wrapper"]/div/div[@ng-click="toggleDailyTips()"]')
    child_div = card_btn.find_element_by_xpath('.//div')
    if 'active-view' not in child_div.get_attribute('class'):
        # Card view not already active, click to activate
        logg.debug("Card view wasn't active, clicking to activate.")
        card_btn.click()
    else:
        logg.debug("Card view already active.")

    logg.debug('Making sure no challenge cards are above')
    challenge_xpath = '//div[@class="dont-show-challenge-card"]/a'
    is_challenge_card_active = ba.elem_exists(challenge_xpath)
    if is_challenge_card_active:
        ba.click('//div[@class="dont-show-challenge-card"]/a')

    # Iterate through cards (2)
    for i in range(0, 2):
        is_tf_btn = False
        # Get the 'done' button
        ba.scroll_absolute('up')
        done_btn = ba.get_elem('//div[@class="card-options-wrapper"]/*/button[@id="triggerCloseCurtain"]')
        ba.scroll_absolute(direction='0,20')
        if done_btn is None:
            logg.debug('Done button not found. Attempting to find a TF button')
            tf_btns = ba.get_elem('//div[@class="card-options-wrapper"]/*/button', single=False)
            if len(tf_btns) > 0:
                logg.debug(f'Found {len(tf_btns)} matching buttons. Using first.')
                done_btn = tf_btns[0]
                is_tf_btn = True
        try:
            done_btn.click()
            logg.debug('Done button most likely clicked.')
        except:
            logg.debug('Done button missing. Trying to click the True button instead.')

        if is_tf_btn:
            # We have one more button to click
            complete_btn = ba.get_elem('//div[@class="card-options-wrapper"]/*/button[@ng-click="completeCard(card)"]')
            try:
                complete_btn.click()
                logg.debug('TF complete button most likely clicked.')
            except:
                logg.debug('TF complete button missing. Wasn\'t able to click it.')

        ba.fast_wait()


def financial_wellness():
    fw_url = 'https://www.moneyhabits.co/virginpulse'
    ba.get(fw_url)
    ba.medium_wait()
    budget_url = 'https://www.moneyhabits.co/web-fe/budgeting'
    ba.get(budget_url)
    ba.medium_wait()

    if today.strftime('%d') == 1:
        # First of month, adjust budget
        ba.get(budget_url)
        ba.click('//div/button[contains(text(), "Set Budget"]')


def fitness_tracker():
    url_dict = {
        'base': 'https://www.myfitnesspal.com',
        'tgt': '2019-01-24',
        'today': today.strftime('%F'),
        'user': 'obrock2'
    }
    # Add in extra url bits
    url_dict['extras'] = 'from_meal=0&username={user}'.format(**url_dict)

    fitness_url = '{base}/account/login'.format(**url_dict)
    ba.get(fitness_url)
    ba.medium_wait()

    ba.enter('//input[@id="username"]', creds['user'])
    ba.enter('//input[@id="password"]', creds['password'])
    ba.click('//input[@type="submit"]')
    ba.medium_wait()

    logg.debug('Going to food diary')
    food_diary_url = '{base}/food/diary'.format(**url_dict)
    ba.get(food_diary_url)

    # Quick add calories
    logg.debug('Copying meal from {tgt} to {today}'.format(**url_dict))
    quick_add_url = '{base}/food/copy_meal?date={today}&from_date={tgt}&{extras}'.format(**url_dict)
    ba.get(quick_add_url)
    ba.medium_wait()


def recipes_section():
    """Go through the recipes section"""
    recipe_url = 'https://member.virginpulse.com/devices/zipongosso'
    ba.get(recipe_url)
    ba.slow_wait()
    # If popup, disable
    logg.debug('Attempting to close popup')
    ba.click('//div[@id="interstitial-content-close"]/span')
    logg.debug('Popup closing procedure done')

    # Meal buttons to click
    logg.debug('Getting meal buttons')
    meal_btns = ba.get_elem('//button[@class="button-green dash-meal-button"]', single=False)
    meal_btns[1].click()
    logg.debug('Clicked meal button')
    ba.slow_wait()

    if today.strftime('%a') == 'Mon':
        logg.info('Today\'s Monday, performing weekly activities')
        # If a monday, favorite a recipe and add to grocery list
        # Favorite (once weekly)
        logg.info('Favoriting recipe')
        fav = ba.get_elem('//div[contains(@class, "favorite") and div[@class="heart"]]')
        if 'is-favorite' in fav.get_attribute('class'):
            logg.debug('Recipe we selected was already favorited. Toggling.')
            # Unfavorite
            fav.click()
        # Favorite again
        fav.click()

        if 'is-favorite' not in fav.get_attribute('class'):
            # Click the heart's parent
            logg.error("Heart click didn't work. Trying to click the favourite button instead.")
            ba.medium_wait()

        logg.info('Adding recipe to grocery list')
        # Add to grocery list (once weekly)
        ba.scroll_absolute('up')
        ba.click('//div[@class="action-text"]/span[text()="Add to Grocery List"]')
        ba.medium_wait()
        # Confirm add
        ba.scroll_absolute('down')
        # First we need to make the recipe section smaller
        recipe_container = ba.get_elem('//div[contains(@class, "grocery-list-add-modal-recipe")]')
        ba.add_style_to_elem(recipe_container, 'height:10px;')
        ba.fast_wait()
        # Now that the element is in view we can click it
        ba.click('//div[@class="grocery-list-add-modal-confirm-container"]/button')
        ba.medium_wait()


def healthy_habits():
    """Scroll through and complete the healthy habits items"""
    hh_url = "https://app.member.virginpulse.com/#/healthyhabits"
    ba.get(hh_url)
    ba.medium_wait()
    yes_btns = ba.get_elem('//div/button[contains(@class, "btn-choice-yes")]', single=False)
    logg.debug(f'{len(yes_btns)} yes buttons found.')

    clicks = 0
    click_limit = 10  # overkill, but we'll keep it
    for i in range(0, len(yes_btns)):
        # In case we get a stale element exception, keep refreshing our yes button inventory
        yes_btns = ba.get_elem('//div/button[contains(@class, "btn-choice-yes")]', single=False)
        yes_btn = yes_btns[i]
        yes_id = yes_btn.get_attribute('id')
        if clicks > click_limit:
            logg.debug('Click limit reached. Breaking loop.')
            break
        if 'green-button' not in yes_btn.get_attribute('class'):
            # Button not clicked
            try:
                ba.scroll_to_element(yes_btn)
                # yes_btn.click() # Commented this out as it seems clicks are more predictable when done through JS
                ba.click_by_id(yes_id)
                logg.debug(f'Clicked button {yes_id}')
                clicks += 1
            except Exception as e:
                logg.error(f'Couldn\'t click button with id {yes_id}: {e}')
        else:
            logg.debug(f'Button {yes_id} seems to have already been clicked.')

        ba.fast_wait()


def slogger():
    """Sleep log"""
    sleep_url = 'https://app.member.virginpulse.com/#/guide/sleep/2'
    ba.get(sleep_url)
    ba.medium_wait()

    # Open up the Device section
    ba.click('//div[@id="open-device-list-btn"]')
    # Open the Manual section
    ba.click('//div[contains(@class, "device-item") and strong[text() = "Manual Tracking"]]')
    # Open the Enter Sleep Data Button
    ba.click('//div[@aria-labelledby="enterSleepDataButton"]')
    # Make sure start hour is 8
    bed_hr = '//input[@ng-model="times.bed.hour"]'
    ba.clear(bed_hr)
    ba.enter(bed_hr, 8)
    # Make sure wake hour is 4
    wake_hr = '//input[@ng-model="times.wake.hour"]'
    ba.clear(wake_hr)
    ba.enter(wake_hr, 4)
    # Enter the data
    ba.click('//div[@class="actions"]/button[text() = "Track It!"]')


def whil_session():
    """Go to the WHIL page and play a video"""
    whil_url = "https://connect.whil.com/virginpulsesso/redirect?destination=home"
    ba.get(whil_url)
    ba.medium_wait()
    # Play a specific session
    body_sense_url = "https://connect.whil.com/goaltags/thrive-mindfulness-101/sessions/sense-the-body"
    ba.get(body_sense_url)
    ba.medium_wait()
    ba.click('//*/img[@alt="play"]')
    # Wait five-ish mins
    time.sleep(310)


message_channel_and_log('Vpulse script booted up')
today = dtt.today()
ba = BrowserAction(logg.log_name, 'chrome', headless=not debug)
logg.debug('Chrome instantiated.')

vpulse_home_url = 'https://member.virginpulse.com/'
points_url = 'https://app.member.virginpulse.com/#/rewards/earn'
ba.get(vpulse_home_url)
ba.slow_wait()

ba.enter('//input[@id="username"]', creds['user'])
ba.enter('//input[@id="password"]', creds['password'])
ba.click('//input[@id="kc-login"]')
ba.medium_wait()
# Look for a security check
sec_form = ba.elem_exists('//input[@value="Send code"]')
if sec_form:
    message_channel_and_log(f'<@{user_me}>, Security code was requested. '
                            f'This script will have to be rerun manually later.')

message_channel_and_log('Logged in.')
ba.slow_wait()

# Get the amount of points we have before operations
ba.get(points_url)
ba.fast_wait()
points_dict = {'pre_points': get_vpoints()}
ba.scroll_absolute(direction='up')
logg.debug(f'Recorded points before starting: {points_dict["pre_points"]:,}')
ba.get(vpulse_home_url)
ba.fast_wait()

# Establish an order to go through the different tasks
tasks_dict = {
    'popup closer': initial_popup_closer,
    'daily cards': daily_cards,
    # 'financial wellness': financial_wellness,
    'fitness tracker': fitness_tracker,
    'healthy recipes': recipes_section,
    'healthy habits': healthy_habits,
    'WHIL session': whil_session,
    'sleep logger': slogger,
}

for task_name, task in tasks_dict.items():
    logg.debug(f'Beginning {task_name} section.')
    try:
        task()
        message_channel_and_log(f'Completed section: {task_name}')
    except Exception as e:
        err_msg = f'Error occurred in section: {task_name}'
        logg.error_with_class(e, err_msg)
        message_channel_and_log(err_msg)

# Collect points after all operations
ba.get(points_url)
ba.medium_wait()
points_dict['post_points'] = get_vpoints()
logg.debug(f'Recorded points after operations: {points_dict["post_points"]:,}')
pre, post = points_dict.values()
message_channel_and_log(f'*Completion report:*\n\tPoints at start: `{pre:,}`\n\tPoints at end: `{post:,}`\n\t'
                        f'Difference: `{post-pre:+,}`\n\tRemaining: `{18000-post:,}`')

logg.debug('Script complete. Quitting instance.')
ba.tear_down()
message_channel_and_log('Competed script. Instance torn down.')
logg.close()
