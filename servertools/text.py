#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import re
from random import randint


class MarkovText:
    def __init__(self, bulk_text, limit=0):
        self.mkov = __import__('markovify')
        if isinstance(bulk_text, list):
            # Multiple models
            models = []
            for i in bulk_text:
                if 0 < limit < len(i):
                    # If character limit, randomly select group of text
                    # Set range to randomly select text chunk
                    max_char = len(i) - limit
                    min_char = limit
                    i_char = randint(min_char, max_char)
                    i = i[i_char:i_char + limit]

                m = self.mkov.Text(i)
                models.append(m)
            self.model = self.mkov.combine(models)
        if isinstance(bulk_text, dict):
            models = []
            for i in list(bulk_text.values()):
                if 0 < limit < len(i):
                    # If character limit, randomly select group of text
                    # Set range to randomly select text chunk
                    max_char = len(i) - limit
                    min_char = limit
                    i_char = randint(min_char, max_char)
                    i = i[i_char:i_char + limit]
                m = self.mkov.Text(i)
                models.append(m)
            self.model = self.mkov.combine(models)
        else:
            self.model = self.mkov.Text(bulk_text)

    def generate_n_sentences(self, n, char_limit=0):
        sentences = []
        for i in range(n):
            s = self.generate_sentence(char_limit)
            if len(s) >= char_limit / 2:
                sentences.append(s)
        return sentences

    def generate_sentence(self, char_limit=0):
        if char_limit > 0:
            return self.model.make_short_sentence(char_limit)
        else:
            return self.model.make_sentence()


class WebExtractor:
    def __init__(self):
        self.bs4 = __import__('bs4')
        self.bs = self.bs4.BeautifulSoup

    def get_matching_elements(self, url, element='p'):
        respond = requests.get(url)
        soup = self.bs(respond.text, 'lxml')
        return soup.find_all(element)

    def get_links(self, url, url_match=''):
        items = self.get_text(url, 'a')
        url_list = []
        for item in items:
            # Determine if element has href attribute
            attr = None
            try:
                attr = item._attr_value_as_string('href')
            except:
                pass
            if attr is not None:
                if url_match == '':
                    url_list.append(attr)
                elif url_match in attr:
                    url_list.append(attr)
        return url_list


class TextCleaner:
    def __init__(self):
        pass

    def process_text(self, text):
        regex_pattern = '[\(\[].*?[\)\]]'  # pattern to remove brackets and their info
        rem_chars = "()[]{}«»"  # characters to explicitly remove from the string
        # eliminate brackets and text with brackets
        text = re.sub(regex_pattern, '', text)
        # eliminate any special characters
        for ch in list(rem_chars):
            if ch in text:
                text = text.replace(ch, '')
        # fix any issues with strings having no space after periods
        space_fixes_find = [r'\.(?! )', r'\?(?! )', r'\!(?! )']
        space_fixes_rep = ['. ', '? ', '! ']
        for s in range(0, len(space_fixes_find)):
            text = re.sub(space_fixes_find[s], space_fixes_rep[s], re.sub(r' +', ' ', text))
        return text

    def sentence_filler(self, text, limit):
        if len(text) < limit:
            diff = limit - len(text)
            if diff > 7:
                # continue if difference is greater than space needed for hashtags
                splts = text.split(sep=' ')
                words = []
                for word in splts:
                    wd = word.replace('.', '')
                    if len(wd) > 3 and wd not in words:
                        words.append(wd)

                # sort word list by word size
                words = sorted(words, key=len, reverse=True)
                hashtags = ''
                # Go through top five words, add them as hashtag

                c = 0
                while c < 50:
                    # try up to 50 times
                    addtag = ' #' + words[randint(0, len(words) - 1)]
                    if len(hashtags) + len(addtag) <= diff:
                        # if tags with new hashtag fits, add it
                        hashtags += addtag
                    c += 1
                text += hashtags
        return text


class TextHelper:
    """
    Text manipulation tool for repetitive tasks
    """
    def __init__(self):
        pass

    def mass_replace(self, find_strings, replace_strings, in_text):
        """
        Performs multiple replace commands for lists of strings
        Args:
            find_strings: list of strings to find
            replace_strings: list of strings to replace find_strings with
            in_text: string to perform replacements
        Note:
            1.) len(replace_strings) == len(find_strings) OR
            2.) len(find_strings) > 1 and len(replace_strings) == 1
        """
        # Replace multiple strings at once
        for x in range(0, len(find_strings)):
            if isinstance(replace_strings, list):
                if len(replace_strings) != len(find_strings):
                    raise ValueError('Lists not the same size!')
                else:
                    in_text = in_text.replace(find_strings[x], replace_strings[x])
            else:
                in_text = in_text.replace(find_strings[x], replace_strings)
        return in_text

    def txt_to_list(self, path_to_txt, delimiter):
        """Convert txt in file to list with provided character serving as delimiter"""
        with open(path_to_txt) as f:
            txtstr = f.read().split(delimiter)
            if ''.join(txtstr) == '':
                txtlist = []
            else:
                txtlist = list(map(int, txtstr[:len(txtstr)]))
        return txtlist
