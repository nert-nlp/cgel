import sys
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches
from itertools import chain
import fileinput

MODE = ['tags', 'trees'][1]
PUNCT = [True, False][0]
#with open('datasets/twitter.cgel') as f, open('datasets/ewt.cgel') as f2, open('datasets/ewt-new1-nschneid.cgel') as f3:
for tree in cgel.trees(fileinput.input()):
    print(tree.tagging(gap_symbol='_.') if MODE=='tags' else tree.ptb(punct = PUNCT, complex_lexeme_separator='_'))
