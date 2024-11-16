import sys, traceback
import argparse
import cgel
from cgel import Node
from collections import Counter
from math import log
from difflib import get_close_matches
from itertools import chain

def main(cgelpaths, punct: bool=False):
    nWarn = 0
    nFormat = 0
    for cgelFP in cgelpaths:
        with open(cgelFP) as f:
            print(cgelFP, file=sys.stderr)
            reqfields = ['tree_by'] if 'oneoff' in cgelFP else []
            nFailures = 0
            for tree in cgel.trees(f, check_format=True, required_fields=reqfields):
                # check_format=True ensures that the generated tree structure matches the input

                # also check that the sentence line matches
                s = tree.sentence(gaps=True, punct=False)
                if tree.sent!=s:
                    print('format error: sent/terminals mismatch (no punct)',
                          tree.sent, s, sep='\n  ', file=sys.stderr)
                    nFormat += 1
                if punct:   # check punctuation (slightly fuzzy match)
                    s = tree.sentence(gaps=False, punct=True, double_period=False)
                    # dollar signs may get reordered, so just check that their count matches
                    assert tree.text.count('$')==s.count('$')
                    # ignore hyphens, which may be added or removed due to stylistic preference
                    t = tree.text.lower().replace(' ','').replace('$','').replace('’',"'").replace('-','')
                    s = s.lower().replace(' ','').replace('$','').replace('’',"'").replace('-','')
                    if t!=s:
                        print('format error: text/terminals mismatch (w/ most punct, ignoring spaces/hyphens)',
                              tree.text, t, s, sep='\n  ', file=sys.stderr)
                        nFormat += 1

                try:
                    _nWarn = tree.validate() # warning count is cumulative
                    nWarn = _nWarn
                except AssertionError as ex:
                    nFailures += 1
                    print('catching AssertionError in validate_trees.py', file=sys.stderr)
                    print(ex, file=sys.stderr)
                    traceback.print_tb(ex.__traceback__, limit=2)
                    print("", file=sys.stderr)

    print(f'{nWarn+nFailures} warnings/notices and {nFormat} format errors', file=sys.stderr)

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Validate well-formedness of CGEL tree annotations.')
    parser.add_argument('files', type=str, nargs='*',
                        help='.cgel file paths')
    parser.add_argument('--punct', action=argparse.BooleanOptionalAction,
                        help='whether to check that punctuation in `text` metadata is present in the tree')

    args = parser.parse_args()
    if args.files:
        main(args.files, punct=args.punct)
    else:
        main(['datasets/ewt.cgel', 'datasets/twitter.cgel', 'datasets/ewt-test_pilot5.cgel', 'datasets/ewt-test_iaa50.cgel'], punct=args.punct)
