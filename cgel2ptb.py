import sys
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches
from itertools import chain

MODE = ['tags', 'trees'][1]
with open('datasets/twitter.cgel') as f, open('datasets/ewt.cgel') as f2, open('datasets/ewt-new1-nschneid.cgel') as f3:
    for tree in cgel.trees(chain(f,f2,f3)):
        print(tree.tagging(gap_symbol='_.') if MODE=='tags' else tree.ptb())
