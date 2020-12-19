from servertools import XPathExtractor, SlackComm
from kavalkilu import LogWithInflux


logg = LogWithInflux('wotd')
scom = SlackComm()
viktor = SlackComm(bot='viktor')

wotd_url = 'https://www.dictionary.com/e/word-of-the-day/'
extractor = XPathExtractor(wotd_url)
tree = extractor.tree
# Get the most recent WOTD
wotd = tree.xpath('//div[contains(@class, "wotd-items")]/div')[0]

word = extractor.xpath_with_regex(wotd, './/div[re:match(@class, "w?otd-item-headword__word")]/h1')
if len(word) > 0:
    word = word[0].text
else:
    raise ValueError('Unable to find primary section for WOTD')
pronunc = ''.join(extractor.xpath_with_regex(
    wotd, './/div[re:match(@class, "w?otd-item-headword__pronunciation")]')[0].itertext()).strip()

# Break down part of speech & definition
pos_block = extractor.xpath_with_regex(
    wotd, './/div[re:match(@class, "w?otd-item-headword__pos")]/p')
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

scom.st.send_message('word-of-the-day', message='Word of the day!', blocks=blocks)
viktor.st.send_message('linky-guistics', message='Word of the day!', blocks=blocks)

logg.close()
