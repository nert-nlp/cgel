import sys, traceback
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches
from itertools import chain

def main(cgelpaths):
    for cgelFP in cgelpaths:
        with open(cgelFP) as f:
            print(cgelFP, file=sys.stderr)
            nFailures = 0
            for tree in cgel.trees(f, check_format=True):
                # check_format=True ensures that the generated tree structure matches the input

                # also check that the sentence line matches
                s = tree.sentence(gaps=True)
                assert tree.sent==s,(tree.sent,s)

                try:
                    _nWarn = tree.validate() # warning count is cumulative
                    nWarn = _nWarn
                except AssertionError as ex:
                    nFailures += 1
                    print('catching AssertionError in validate_trees.py', file=sys.stderr)
                    print(ex, file=sys.stderr)
                    traceback.print_tb(ex.__traceback__, limit=1)
                    print("", file=sys.stderr)

    print(f'{nWarn+nFailures} warnings/notices', file=sys.stderr)

if __name__=='__main__':
    if sys.argv[1:]:
        main(sys.argv[1:])
    else:
        main(['datasets/ewt.cgel', 'datasets/twitter.cgel', 'datasets/ewt-test_pilot5.cgel', 'datasets/ewt-test_iaa50.cgel'])
