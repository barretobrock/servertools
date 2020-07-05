from servertools import XPathExtractor, SlackComm
from kavalkilu import Log


logg = Log('emoji-scraper', log_to_db=True)
scom = SlackComm()

wotd_url = 'https://www.dictionary.com/e/word-of-the-day/'
tree = XPathExtractor(wotd_url).tree
# Get the most recent WOTD
wotd = tree.findall('//div[@class="wotd-items"]/div[@class="wotd-item-wrapper"]')[0]


word = wotd.find('.//div[@class="wotd-item-headword__word"]/h1').text
pronunc = ''.join(wotd.find('.//div[@class="wotd-item-headword__pronunciation"]').itertext()).strip()

# Break down part of speech & definition
pos_block = wotd.findall('.//div[@class="wotd-item-headword__pos"]')[0].getchildren()
pos = ''.join(pos_block[0].itertext()).strip()
definition = ''.join(pos_block[1].itertext()).strip()

# Break down the origin section
origin = wotd.xpath('.//div[contains(@class, "wotd-item-origin__content")]')[0]
origin_title = origin.find('./h2').text
origin_text = ''.join(origin.find('./p').itertext())

# Break out examples
example = wotd.find('.//div[@class="wotd-item-examples wotd-item-examples--last"]')
examples = example.findall('./div/div[@class="wotd-item-example__content"]')
example_txt = ""
for example in examples:
    example_txt += f'>{"".join(example.itertext()).strip()}\n\n'

bkb = scom.bkb
blocks = [
    bkb.make_context_section([
        f'Word of the Day: *`{word}`* _`{pronunc}`_',
        f'{pos}, _`{definition}`_'
    ]),
    bkb.make_block_divider(),
    bkb.make_block_section(f'*{origin_title}*\n\n{origin_text}'),
    bkb.make_block_divider(),
    bkb.make_block_section(f'*Example Usage*\n\n{example_txt}_Try using it in an email today!_')
]

scom.st.send_message('wotd', message='', blocks=blocks)

logg.close()
