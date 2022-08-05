import sys
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches
from itertools import chain

nWarn = 0
with open('datasets/twitter.cgel') as f, open('datasets/ewt.cgel') as f2:
    for tree in cgel.trees(chain(f,f2), check_format=True):
        # check_format=True ensures that the generated tree structure matches the input

        # also check that the sentence line matches
        s = tree.sentence(gaps=True)
        assert tree.sent==s,(tree.sent,s)

        nWarn += tree.validate()

print(f'{nWarn} warnings/notices', file=sys.stderr)
