import sys
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches
from itertools import chain

def main(cgelpaths):
    for cgelFP in cgelpaths:
        with open(cgelFP) as f:
            for tree in cgel.trees(f, check_format=True):
                # check_format=True ensures that the generated tree structure matches the input

                # also check that the sentence line matches
                s = tree.sentence(gaps=True)
                assert tree.sent==s,(tree.sent,s)

                nWarn = tree.validate() # warning count is cumulative

    print(f'{nWarn} warnings/notices', file=sys.stderr)

if __name__=='__main__':
    if sys.argv[1:]:
        main(sys.argv[1:])
    else:
        main(['datasets/ewt.cgel', 'datasets/twitter.cgel'])
