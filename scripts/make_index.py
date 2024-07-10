import sys, traceback
import argparse
import glob
import math
import cgel
from cgel import Node
from collections import Counter, defaultdict
from math import log
from difflib import get_close_matches
from itertools import chain

"""
Run as 
"""

def main(cgelpaths):
    print('# CGELBank Index\n\n')
    print(len(cgelpaths), ' files\n')
    print('''Below are:
  - Per-file sentence listing with ID and |lexical node, gap| counts
  - [Annotator notes](#notes)
  - [Infrequent categories](#infrequent-categories)
  - [Infrequent functions](#infrequent-functions)

See also: [STATS.md](STATS.md)
''')
    notes = []
    cats = defaultdict(set)
    fxns = defaultdict(set)
    nTrees = 0
    for cgelFP in cgelpaths:
        print(f'## [{cgelFP.replace("datasets/","")}]({cgelFP})\n')
        with open(cgelFP) as f:
            print(cgelFP, file=sys.stderr)
            for tree in cgel.trees(f):
                nTrees += 1
                nWords = len(tree.terminals(gaps=False))
                nGaps = len(tree.terminals(gaps=True)) - nWords
                sentId = f'`{tree.sentid}`' if tree.sentid is not None else ''
                if 'oneoff' in cgelFP:
                    d0, d1 = cgelFP.rsplit('/',1)
                    k = d1.replace('.cgel','')
                    sentId = (f'[{k}]({d0}/pdf/{k}.pdf) ' + sentId).strip()
                print(f'- {sentId} |{nWords}, {nGaps}| {tree.text}')
                for node in tree.tokens.values():
                    if node.note:
                        notes.append((node.note, sentId))
                    cats[node.constituent].add(sentId)
                    fxns[node.deprel].add(sentId)
        print()
    print()
    print(f'# Notes\n')
    for note,sentId in sorted(notes):
        print(f'- {note} <small>({sentId})</small>')
    print()
    print('# Infrequent Categories\n')
    thresh = math.floor(nTrees*.05)
    print(f'Of {nTrees} trees, the following occurred in fewer than 5% ({thresh}):\n')
    for k,v in cats.items():
        if len(v)<thresh:
            print(f'- `{k}` ({len(v)}): <small>' + ', '.join(v) + '</small>')
    print()
    print('# Infrequent Functions\n')
    for k,v in fxns.items():
        if len(v)<thresh:
            print(f'- `{k}` ({len(v)}): <small>' + ', '.join(v) + '</small>')
    print()

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Generate Markdown file with lists of sentences and their properties.')
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
