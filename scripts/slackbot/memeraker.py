"""Message links to memes for Viktor to post periodically"""
import os
import re
import time
import numpy as np
from typing import List
from datetime import datetime, timedelta
from slacktools import SlackTools
from kavalkilu import Keys, Log


logg = Log('memeraker')
vcreds = Keys().get_key('viktor_creds')
st = SlackTools(**vcreds)
user_me = 'UM35HE6R5'

# Wine review text & previous stop timestamp
ddir = os.path.join(os.path.expanduser('~'), 'data')
fpath = os.path.join(ddir, 'mkov_wines.txt')
ts_path = os.path.join(ddir, 'last_memeraker_ts')


def post_memes(reviews: List[str], memes: List[str], wait_min: int = 5, wait_max: int = 60):
    # Begin the upload process, include a review
    for meme in memes:
        review = np.random.choice(reviews, 1)[0]
        st.upload_file('memes-n-shitposts', meme, 'image', is_url=True, txt=review)
        # Wait some seconds before posting again
        wait_s = np.random.choice(range(wait_min, wait_max), 1)[0]
        logg.debug(f'Waiting {wait_s}s.')
        time.sleep(wait_s)


# Read in the last timestamp. if nothing, default to one hour ago
if os.path.exists(ts_path):
    with open(ts_path) as f:
        last_timestamp = datetime.fromtimestamp(float(f.read().strip()))
    logg.debug(f'Found timestamp of {last_timestamp}')
else:
    last_timestamp = (datetime.now() - timedelta(minutes=60))
    logg.debug(f'No pre-existing timestamp found. Setting as {last_timestamp}')


# Scan Viktor's dms from up to 5 mins ago
msgs = st.search_messages_by_date(channel='memeraker', after_date=last_timestamp,
                                  after_ts=last_timestamp, max_results=100)
# Search results are ordered from the most recent, so set the most recent one
# as the timestamp to look from at the next instantiation of this script
if len(msgs) > 0:
    logg.debug('Rewriting timestamp file with latest result\'s timestamp')
    # Rewrite the timestamp file
    with open(ts_path, 'w') as f:
        f.write(msgs[0]['ts'])

# Filter messages that have a non-empty text field
msgs = [x for x in msgs if x['text'] != '']
logg.debug(f'Found {len(msgs)} message(s) in DM channel from the given time range!')

# We've gotten the messages that were sent only recently. Now let's try to parse out the memes!
meme_links = []
for msg in msgs:
    content = msg['text']
    # Parse out the individual links by splitting on newlines/spaces
    raw_links_list = re.split(r'\s+', content)
    for raw_link in raw_links_list:
        # Try to parse out the link
        link = re.search(r'https.*\.(jpe?g|png)', raw_link)
        if link is not None:
            meme_links.append(link.group())

logg.debug(f'{len(meme_links)} link(s) successfully parsed.')
if len(meme_links) > 0:
    # Load the reviews
    with open(os.path.join(ddir, fpath)) as f:
        reviews = [rev.rstrip() for rev in f.readlines()]
    # Handle meme posting
    post_memes(reviews, meme_links, 5, 60)

logg.debug('Memeraker finished. Shutting down.')
logg.close()
