import os
import nltk
import pandas as pd
from servertools import MarkovModel

nltk.download('averaged_perceptron_tagger')
ddir = os.path.join(os.path.expanduser('~'), 'Downloads')
mk1_src = os.path.join(ddir, 'mk1.txt')
mk2_src = os.path.join(ddir, 'mk2.txt')
lyrics = os.path.join(ddir, 'lyrics-data.csv')

df = pd.read_csv(lyrics)
df = df[df['Idiom'] == 'ENGLISH']
df = df[['Lyric']]
df.head(70000).to_csv(os.path.join(ddir, 'mk2.txt'), header=False, index=False, sep=' ')

mk = MarkovModel(fpath=[mk1_src, mk2_src], do_compile=True)

# mk1 = MarkovModel(fpath=mk1_src, do_compile=True)
mk2 = MarkovModel(fpath=mk2_src, do_compile=True)
mk2.generate_sentence(posify=True)
