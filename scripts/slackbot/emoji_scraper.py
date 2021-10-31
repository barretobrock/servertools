"""Checks slackmojis daily for new additions"""
import json
import pathlib
from kavalkilu import (
    Path,
    LogWithInflux
)
from servertools import (
    SlackComm,
    XPathExtractor
)


logg = LogWithInflux('emoji-scraper')
scom = SlackComm(bot='viktor', parent_log=logg)

mojis_path = pathlib.Path().home().joinpath('data/slackmojis.json')
p = Path()
fpath = p.easy_joiner(p.data_dir, 'slackmojis.json')
chan = 'emoji_suggestions'
url = 'https://slackmojis.com/emojis/recent'
xpath_extractor = XPathExtractor(url)

emoji_list = xpath_extractor.xpath('//ul[@class="emojis"]', single=True)
emojis = emoji_list.getchildren()

# Read in the previous emoji id list
if not p.exists(fpath):
    prev_emojis = {}
else:
    with open(fpath) as f:
        prev_emojis = json.loads(f.read())

new_emojis = {}
for emoji in emojis:
    emo_id = emoji.getchildren()[0].get('data-emoji-id-name')
    emo_name = emoji.getchildren()[0].getchildren()[1].text.strip()
    if emo_id not in prev_emojis.keys():
        # Get link and add to the id list
        emo_link = emoji.findall('.//img')[0].get('src')
        if emo_link is not None:
            new_emojis[emo_id] = {
                'name': emo_name,
                'link': emo_link
            }

customize_url = f'https://{scom.st.team}.slack.com/customize/emoji?utm_source=in-prod&' \
                f'utm_medium=inprod-customize_link-slack_menu-click'
help_text = f"""
*Emoji Upload Process*
 - Open the image in a browser (click the link or right click the image -> "open link")
 - Right click image -> `Save image as...` 
 - Go to the <{customize_url}|custom emoji page> for OKR
 - Click `Add Custom Emoji`
 - Upload file & give it a unique name! 
"""

if len(new_emojis) > 0:
    blocks = [
        scom.bkb.make_context_section('New Emojis :postal_horn::postal_horn::postal_horn:')
    ]
    for name, e_dict in new_emojis.items():
        blocks.append(
            scom.bkb.make_block_section(f'<{e_dict["link"]}|{e_dict["name"].replace(":", "")}>',
                                        accessory=scom.bkb.make_image_element(e_dict['link'], 'emoji'))
        )
    # Iterate through blocks. Slack limits posts by 50 blocks.
    for i in range(0, len(blocks), 50):
        logg.debug(f'Sending message block {i + 1}')
        scom.st.send_message(channel=chan, message='Emoji Report!', blocks=blocks[i: i + 50])
    prev_emojis.update(new_emojis)
else:
    logg.debug('No new emojis to send.')

# Save data to path
with open(fpath, 'w') as f:
    json.dump(prev_emojis, f)

logg.close()
