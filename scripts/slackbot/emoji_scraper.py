"""Checks slackmojis daily for new additions"""
import sys
import time
import json
from urllib.request import Request, urlopen
from lxml import etree
from slacktools import SlackTools
from kavalkilu import Keys, Path, Log


logg = Log('emoji-scraper')
vcreds = Keys().get_key('viktor_creds')
st = SlackTools(**vcreds)

p = Path()
fpath = p.easy_joiner(p.data_dir, 'slackmojis.json')
chan = 'emoji_suggestions'
url = 'https://slackmojis.com/emojis/recent'
req = Request(url, headers={'User-Agent': 'Magic Browser'})
resp = urlopen(req)
if resp.code != 200:
    # unsuccessful attempt, but still notify the channel
    st.send_message(chan, f'Failed to pull slackmoji report: {resp.status_code}')
    sys.exit(1)

htmlparser = etree.HTMLParser()
tree = etree.parse(resp, htmlparser)

emoji_list = tree.findall('//ul[@class="emojis"]')[0]
emojis = emoji_list.getchildren()

# Read in the previous emoji id list
with open(fpath) as f:
    prev_emos = json.loads(f.read())

new_emojis = {}
for emoji in emojis:
    emo_id = emoji.getchildren()[0].get('data-emoji-id-name')
    emo_name = emoji.getchildren()[0].getchildren()[1].text.strip()
    if emo_id not in prev_emos.keys():
        # Get link and add to the id list
        emo_link = emoji.findall('.//img')[0].get('src')
        if emo_link is not None:
            new_emojis[emo_id] = {
                'name': emo_name,
                'link': emo_link
            }

if len(new_emojis) > 0:
    st.send_message('emoji_suggestions', 'Found some new emojis from slackmojis!')
    for name, e_dict in new_emojis.items():
        st.send_message('emoji_suggestions', f'<{e_dict["link"]}|{e_dict["name"]}>')
        time.sleep(10)
    prev_emos.update(new_emojis)

# Save data to path
with open(fpath, 'w') as f:
    json.dump(prev_emos, f)

logg.close()
