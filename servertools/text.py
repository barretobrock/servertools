#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import json
from random import randint
from typing import (
    Union,
    List
)
import nltk
import markovify
from markovify import Text
from urllib.request import (
    Request,
    urlopen
)
from lxml import etree
from lxml.etree import (
    _ElementTree,
    _Element
)


class MarkovText(Text):
    def __init__(self, text: str = None, fpath: str = None, state_size: int = 2):
        """
        Reads in text either directly or from path
        Args:
            text: str, the exact blob of text to train on
            fpath: str, the location of the file containing the text
            state_size: int, number of words the probability of the next word depends on. default = 2
        """
        if text is None and fpath is not None:
            # Read from path
            with open(fpath) as f:
                text = f.read()
        elif text is not None:
            # Read from variable
            pass
        else:
            # Both are None; raise an error
            raise ValueError('Please pass a variable for either test or fpath.')
        super().__init__(text, state_size=state_size)


class MarkovModel:
    def __init__(self, text: Union[str, List[str]] = None, fpath: Union[str, List[str]] = None,
                 model_path: str = None, weights: Union[List[int], List[float]] = None,
                 state_size: int = 2, do_compile: bool = False):
        """
        Builds the actual model to generate sentences from
        Args:
            text: str or list of str, the source text(s) to read in.
            fpath: str or list of str, the path to the source text(s) to read in.
            weights: list of int, if used, assigns weight to each model (e.g., 1, 1.5, 2)
            state_size: int, number of words the probability of the next word depends on. default = 2
            do_compile: bool, if True, will compile the model to be a bit more performant
        """
        self.model = None

        if model_path is not None:
            # Read in pre-built model from path
            with open(model_path) as f:
                self.model = Text.from_json(json.load(f))

        if fpath is not None and self.model is None:
            # Read in text from path
            if isinstance(fpath, str):
                fpath = [fpath]
            text = []
            for fp in fpath:
                with open(fp) as f:
                    text.append(f.read())

        if self.model is None:
            if isinstance(text, str):
                self.model = Text(text, state_size=state_size)
            else:
                models = [Text(x, state_size=state_size) for x in text]
                self.model = markovify.combine(models, weights)

        if self.model is None:
            raise ValueError('Pass in a value for either the text for fpath argument.')

        if do_compile:
            self.model.compile(inplace=True)

    def generate_n_sentences(self, n: int, char_limit: int = 0) -> List[str]:
        """Generates a certain number of sentences"""
        sentences = []
        for i in range(n):
            s = self.generate_sentence(char_limit)
            if len(s) >= char_limit / 2:
                # Make sure we're getting a decent amount of sentence
                sentences.append(s)
        return sentences

    def generate_sentence(self, char_limit: int = 0, posify: bool = False) -> str:
        """Generates a sentence"""
        if char_limit > 0:
            sentence = self.model.make_short_sentence(char_limit)
        else:
            sentence = self.model.make_sentence()
        if posify:
            sentence = self._posify_sentence(sentence)
        return sentence

    def _posify_sentence(self, sentence: str) -> str:
        """Uses NLTK's part-of-speech tagger to generate a sentence that
        obeys sentence structure a bit better then a naive model"""
        self._check_nltk_resources()
        words = re.split(self.model.word_split_pattern, sentence)
        words = ['::'.join(tag) for tag in nltk.pos_tag(words)]

        return ' '.join(word.split('::')[0] for word in words)

    @staticmethod
    def _check_nltk_resources():
        """Checks if nltk resources have been downloaded"""
        try:
            nltk.data.find('taggers/averaged_perceptron_tagger.zip')
        except LookupError:
            nltk.download('averaged_perceptron_tagger')

    def save_to_disk(self, path: str):
        """Save the Markov model to disk"""
        with open(path, 'w') as f:
            json.dump(self.model.to_json(), f)


class XPathExtractor:
    """Builds an HTML tree and allows element selection based on XPath"""
    def __init__(self, url: str):
        self.tree = self._get_tree(url)

    @staticmethod
    def _get_tree(url: str) -> _ElementTree:
        req = Request(url, headers={'User-Agent': 'Magic Browser'})
        resp = urlopen(req)
        if resp.code != 200:
            raise ConnectionError(f'Unexpected response to request: {resp.code}')

        htmlparser = etree.HTMLParser()
        return etree.parse(resp, htmlparser)

    @staticmethod
    def get_inner_html(elem: _Element) -> str:
        """Extracts the HTML as text from a given element"""
        return etree.tostring(elem, encoding='utf-8').decode('utf-8')

    @staticmethod
    def read_str_to_html(string: str) -> _Element:
        """Takes a string and reads it in as HTML elements"""
        return etree.fromstring(string)

    @staticmethod
    def get_nth_child(elem: _Element, n: int) -> _Element:
        """Returns the nth child of an element"""
        return elem.getchildren()[n]

    @staticmethod
    def get_attr_from_elems(elem_list: List[_Element], from_attr: str = 'href') -> List[str]:
        """Extracts an attribute from all the elements in a list having that particular attribute field"""
        return [elem.get(from_attr) for elem in elem_list if elem.get(from_attr) is not None]

    def xpath(self, xpath: str, obj: _Element = None, single: bool = False, get_text: bool = False) -> \
            Union[str, _Element, List[_Element]]:
        """Retrieves element(s) matching the given xpath"""
        method = self.tree.xpath if obj is None else obj.xpath
        elems = method(xpath)
        return self._process_xpath_elems(elems, single, get_text)

    @staticmethod
    def class_contains(cls: str) -> str:
        return f'(@class, "{cls}"'

    @staticmethod
    def _process_xpath_elems(elems: List[_Element], single: bool, get_text: bool) -> \
            Union[str, _Element, List[_Element]]:
        if single:
            elems = [elems[0]]

        if get_text:
            return ''.join([x for e in elems for x in e.itertext()])
        else:
            return elems[0] if single else elems

    def xpath_with_regex(self, xpath: str, obj: _Element = None, single: bool = False, get_text: bool = False) ->\
            Union[str, _Element, List[_Element]]:
        """Leverages xpath with regex
        Example:
            >>> self.xpath_with_regex('//div[re:match(@class, "w?ord.*")]/h1')
        """
        method = self.tree.xpath if obj is None else obj.xpath
        elems = method(xpath, namespaces={"re": "http://exslt.org/regular-expressions"})
        elems = self._process_xpath_elems(elems, single, get_text)
        return elems


class TextCleaner:
    def __init__(self):
        pass

    @staticmethod
    def process_text(text: str) -> str:
        regex_pattern = r'[\(\[].*?[\)\]]'  # pattern to remove brackets and their info
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

    @staticmethod
    def sentence_filler(text: str, limit: int) -> str:
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

    @staticmethod
    def mass_replace(find_strings: Union[List[str], str], replace_strings: Union[List[str], str],
                     in_text: str) -> str:
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
        if isinstance(find_strings, str):
            find_strings = [find_strings]

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

    @staticmethod
    def txt_to_list(path_to_txt: str, delimiter: str) -> List[str]:
        """Convert txt in file to list with provided character serving as delimiter"""
        with open(path_to_txt) as f:
            txtstr = f.read().split(delimiter)
            if ''.join(txtstr) == '':
                txtlist = []
            else:
                txtlist = list(map(int, txtstr[:len(txtstr)]))
        return txtlist
