"""Checks slackmojis daily for new additions"""
import sys
import time
import json
from urllib.request import Request, urlopen
from lxml import etree
from servertools import SlackComm
from kavalkilu import Path, LogWithInflux


logg = LogWithInflux('emoji-scraper')
scom = SlackComm()

p = Path()
fpath = p.easy_joiner(p.data_dir, 'slackmojis.json')
chan = 'emoji_suggestions'
url = 'https://slackmojis.com/emojis/recent'
req = Request(url, headers={'User-Agent': 'Magic Browser'})
resp = urlopen(req)
if resp.code != 200:
    # unsuccessful attempt, but still notify the channel
    scom.st.send_message(chan, f'Failed to pull slackmoji report: {resp.status_code}')
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

help_text = """
*Emoji Upload Process*
 - Open the image in a browser (click the link or right click the image -> "open link")
 - Right click image -> `Save image as...` 
 - Go to the <https://orbitalkettlerelay.slack.com/customize/emoji?utm_source=in-prod&utm_medium=inprod-customize_link-slack_menu-click|custom emoji page> for OKR
 - Click `Add Custom Emoji`
 - Upload file & give it a unique name! 
"""

if len(new_emojis) > 0:
    scom.st.send_message(chan, f'Found {len(new_emojis)} new emoji(s) from slackmojis!\n\n'
                               f'{help_text}')
    for name, e_dict in new_emojis.items():
        scom.st.send_message('emoji_suggestions', f'<{e_dict["link"]}|{e_dict["name"]}>')
        time.sleep(10)
    scom.st.send_message(chan, 'That\'s all for now!')
    prev_emos.update(new_emojis)

# Save data to path
with open(fpath, 'w') as f:
    json.dump(prev_emos, f)

logg.close()
