import re
from typing import List
from lxml.etree import _Element
from slacktools import BlockKitBuilder as bkb
from servertools import XPathExtractor, SlackComm
from kavalkilu import LogWithInflux


logg = LogWithInflux('wotd')

wotd_url = 'https://www.dictionary.com/e/word-of-the-day/'
sotd_url = 'https://www.thesaurus.com/e/synonym-of-the-day/'


def italicize_paragraph(text: str, elem: _Element):
    """Formats keywords in paragraph according to Slack's markdown"""
    # Build a list of things to italicise
    italics = []
    for item in elem.iter('em'):
        stripped = item.text.strip()
        if stripped == '' or len(stripped) < 2:
            continue
        italics.append(stripped)
    # Apply italics to origin_text
    for italic in list(set(italics)):
        re_str = f'[\\s]+([\\W]*({italic}))[\\W\\s]*'
        matches = re.finditer(re_str, text)
        # len([x for x in matches])
        for match in matches:
            original = match.group(0)
            replacement = re.sub(r'\s+', ' ', original.replace(match.group(2), f' _`{match.group(2)}`_ '))
            text = text.replace(original, replacement)
    return text


def extract_otd(url: str, is_wotd: bool = False) -> List[dict]:
    """Extract Synonym/Word of the day"""
    xtool = XPathExtractor(url)
    # Get the most recent WOTD
    class_prefix = 'wotd' if is_wotd else 'sotd'
    title_section = 'word' if is_wotd else 'synonym'
    otd = xtool.xpath(f'//div[contains(@class, "{class_prefix}-items")]/div', single=True)

    sotd_xpath = f'.//div[contains(@class, "{class_prefix}-item__title")]'
    wotd_xpath = f'.//div[contains(@class, "otd-item-headword__word")]'
    word = xtool.xpath(wotd_xpath if is_wotd else sotd_xpath, obj=otd, get_text=True).strip()
    # Pronunciation
    pronunc = xtool.xpath('.//div[contains(@class, "otd-item-headword__pronunciation")]', obj=otd,
                          single=True, get_text=True)
    pronunc = re.sub(r'\s+', ' ', pronunc)

    # Extract the part of speech
    if is_wotd:
        # Break down part of speech & definition
        pos_block = xtool.xpath_with_regex('.//div[re:match(@class, "w?otd-item-headword__pos")]/p', obj=otd)
        pos = ''.join(pos_block[0].itertext()).strip()
        definition = ''.join(pos_block[1].itertext()).strip()
        # Break down the origin section
        origin = xtool.xpath('.//div[contains(@class, "wotd-item-origin__content")]', otd, single=True)
        origin_title = origin.find('./h2').text
        origin_text = ''.join(origin.find('./p').itertext())
        origin_text = italicize_paragraph(origin_text, origin)
        desc_section = f'*{origin_title}*\n\n{origin_text}'
        # Break out examples
        example = otd.find('.//div[@class="wotd-item-examples wotd-item-examples--last"]')
        examples = example.findall('./div/div[@class="wotd-item-example__content"]')
        example_txt = ""
        for example in examples:
            example_txt += f'>{"".join(example.itertext()).strip()}\n\n'
        example_section = f'*Example Usage*\n\n{example_txt}_Try using it in an email today!_'
    else:
        pos = pronunc[: pronunc.index('[')].strip()
        pronunc = pronunc[pronunc.index('['):].strip()
        definition = xtool.xpath('.//h2[@class="sotd-item__desc-title"]', otd, single=True, get_text=True)
        definition = re.sub(r'\s+', ' ', definition.strip())
        desc = xtool.xpath('.//div[@class="sotd-item__description"]', otd, single=True, get_text=True)
        desc = re.sub(r'\s+', ' ', desc.strip())
        desc_section = f'*{definition}*\n\n{desc}'
        # Get usages
        usages = xtool.xpath('.//div[@class="sotd-item__usage"]', otd)
        usage_txt = ''
        for usage in usages:
            evidence = xtool.xpath('.//div[@class="sotd-item__usage__evidence"]', usage, get_text=True).strip()
            example = xtool.xpath('.//div[@class="sotd-item__usage__example"]', usage, get_text=True).strip()
            usage_txt += f'*`{evidence}`*\n\t> {example}\n'
        example_section = f'*Commonly Found As*\n\n{usage_txt}_Try using it in an email today!_'

    return [
        bkb.make_context_section([
            f'{title_section.title()} of the Day: *`{word}`* _`{pronunc}`_',
            f'{pos}, _`{definition}`_'
        ]),
        bkb.make_block_divider(),
        bkb.make_block_section(desc_section),
        bkb.make_block_divider(),
        bkb.make_block_section(example_section)
    ]


wotd_blocks = extract_otd(wotd_url, is_wotd=True)
sotd_blocks = extract_otd(sotd_url, is_wotd=False)
blocks = [wotd_blocks, sotd_blocks]

msg_dict = {
    'viktor': 'linky-guistics',
    'sasha': 'word-of-the-day'
}
for k, v in msg_dict.items():
    scom = SlackComm(bot=k, parent_log=logg)
    for block in blocks:
        scom.st.send_message(channel=v, message='Word of the Day!', blocks=block)

logg.close()
