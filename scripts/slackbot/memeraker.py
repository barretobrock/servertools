"""Message links to memes for Viktor to post periodically"""
import os
import re
import sys
import time
import numpy as np
from typing import List
from datetime import datetime, timedelta
from slacktools import SlackTools
from kavalkilu import Keys, Log


logg = Log('memeraker')
vcreds = Keys().get_key('viktor_creds')
st = SlackTools(**vcreds)
# bkb = BlockKitBuilder()
user_me = 'UM35HE6R5'
# Used to select precise start time
x_mins_before = (datetime.now() - timedelta(minutes=60))

# Wine review text
ddir = os.path.join(os.path.expanduser('~'), 'data')
fpath = os.path.join(ddir, 'mkov_wines.txt')


def post_memes(reviews: List[str], memes: List[str], wait_min: int = 5, wait_max: int = 60):
    # Begin the upload process, include a review
    for meme in memes:
        review = np.random.choice(reviews, 1)[0]
        st.upload_file('memes-n-shitposts', meme, 'image', is_url=True, txt=review)
        # Wait some seconds before posting again
        wait_s = np.random.choice(range(wait_min, wait_max), 1)[0]
        logg.debug(f'Waiting {wait_s}s.')
        time.sleep(wait_s)


# Get my dm channel
resp = st.bot.conversations_open(users=user_me)
if resp['ok']:
    channel = resp['channel']['id']
else:
    logg.debug('Could not get DM channel id.')
    logg.close()
    sys.exit(1)

# Scan Viktor's dms from up to 5 mins ago
msgs = st.search_messages_by_date(from_uid=user_me, on_date=x_mins_before, after_ts=x_mins_before)

# Filter messages that were in the DM channel and after the timestamp
logg.debug(f'Found {len(msgs)} message(s) in DM channel from the given time range!')

# We've gotten the messages that were sent only recently. Now let's try to parse out the memes!
meme_links = []
for msg in msgs:
    content = msg['text']
    # Parse out the individual links by splitting on newlines/spaces
    raw_links_list = re.split(r'\s+', content)
    for raw_link in raw_links_list:
        # Try to parse out the link
        link = re.search(r'https.*\.(jpg|png)', raw_link)
        if link is not None:
            meme_links.append(link.group())

logg.debug(f'{len(meme_links)} link(s) parsed.')
if len(meme_links) > 0:
    # Load the reviews
    with open(os.path.join(ddir, fpath)) as f:
        reviews = [rev.rstrip() for rev in f.readlines()]
    # Handle meme posting
    post_memes(reviews, meme_links, 5, 60)

logg.debug('Memeraker finished. Shutting down.')
logg.close()
