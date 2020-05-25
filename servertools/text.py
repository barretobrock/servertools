#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
