import sys
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches
from itertools import chain

MODE = ['tags', 'trees'][0]
with open('datasets/twitter.cgel') as f, open('datasets/ewt.cgel') as f2:
    for tree in cgel.trees(chain(f2,)):
        print(*tree.tagging(gap_symbol='_.').split() if MODE=='tags' else tree.ptb(), sep='\n')
