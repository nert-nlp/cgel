import sys, traceback
import argparse
import glob
import re
import cgel
from cgel import Node

"""
Lists all trees, one per line.
Run in root directory as:

python -m scripts.make_treesfile > all.trees
"""

def main(cgelpaths):
    nTrees = 0
    for cgelFP in cgelpaths:
        with open(cgelFP) as f:
            print(cgelFP, file=sys.stderr)
            for tree in cgel.trees(f):
                print(' '.join(ln.strip() for ln in str(tree).split('\n')))

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Lists all trees, one per line.')
    parser.add_argument('files', type=str, nargs='*',
                        help='.cgel file paths')
    # parser.add_argument('--punct', action=argparse.BooleanOptionalAction,
    #                     help='whether to check that punctuation in `text` metadata is present in the tree')

    args = parser.parse_args()
    if args.files:
        main(args.files)
    else:
        main(['datasets/ewt.cgel', 'datasets/twitter.cgel',
              'datasets/ewt-test_pilot5.cgel', 'datasets/ewt-test_iaa50.cgel',
              'datasets/trial/ewt-trial.cgel', 'datasets/trial/twitter-etc-trial.cgel'] 
              + sorted(glob.glob('datasets/oneoff/*.cgel')))
