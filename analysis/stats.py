import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter, defaultdict
from math import log
from difflib import get_close_matches
from itertools import zip_longest, chain
import argparse

"""
Report stats on CGEL only (without aligning to UD).
In POS mode, also count phrasal categories and functions.
"""

all_files = {
    'twitter': '../datasets/twitter.cgel',
    'ewt': '../datasets/ewt.cgel',
    'pilot': '../datasets/iaa/ewt-test_pilot5.adjudicated.cgel',
    'iaa': '../datasets/iaa/ewt-test_iaa50.adjudicated.cgel'
}

def map_mult(s, olds, new):
    return new if any(o==s for o in olds) else s

def overview(trees: list[cgel.Tree]):
    print("Trees:", len(trees))
    print("Tokens:", sum(t.length for t in trees))
    print("Nodes:", sum(t.size for t in trees))
    print("Length:", sum(t.length for t in trees) / len(trees))
    print("Depth:", sum(t.depth for t in trees) / len(trees))

def analyse_pos(trees):
    cgels = Counter()
    lemmas = Counter()
    cats = Counter()
    fxns = Counter()
    poses_by_lemma = defaultdict(set)
    ambig_class = defaultdict(set)
    fxn_words = {'D': set(), 'N_pro': set(), 'V_aux': set(), 'P': set(), 'Sdr': set(), 'Coordinator': set()}

    # node properties: 'constituent' (POS or phrasal category), 'deprel' (grammatical function), 'head' (index), 'label' (coindexation variable), 'text' (terminals only)
    for cgel_tree in trees:
        for node in cgel_tree.tokens.values():
            if not node.deprel:
                assert node.head==-1
                fxns['(root)'] += 1
            else:
                fxns[node.deprel] += 1

            if node.text:   # terminal
                cgel_pos = node.constituent
                cgels[cgel_pos] += 1
                lemma = node.lemma
                lemmas[lemma] += 1
                poses_by_lemma[lemma].add(cgel_pos)
                if lemma in ('be',) and cgel_pos=='P':
                    assert False,node
                if cgel_pos not in ('V','N','Adj','Adv','Int'):
                    if lemma is not None:   # will be None for deleted words
                        fxn_words[cgel_pos].add(lemma)
            else:  # nonterminal
                if node.constituent in ('N','V','Adj','Adv','D','P','Coordinator','Int','N_pro','Sbr','V_aux'):
                    # most of these are due to preprocessing errors. a couple are legitimate lexical coordinations
                    if node.deprel!='Coordinate':
                        print('weird',node.deprel,node.constituent,cgel_tree.sentence())
                        continue
                    cats[node.constituent+'@coord'] += 1
                else:
                    cats[node.constituent] += 1


    TOP_72 = {'be': 120, 'the': 103, 'to': 83, 'and': 66, 'a': 63, 'of': 52, 'i': 52, 'that': 48, 'have': 41, 'in': 38,
        'it': 29, 'you': 25, 'for': 24, 'they': 22, 'we': 20, 'do': 18, 'on': 18, 'this': 18, 'my': 16, 'at': 15, 'with': 14,
        'so': 14, 'as': 14, 'your': 13, 'not': 13, 'will': 12, 'get': 12, 'he': 12, 'just': 11, 'if': 11, 'can': 11, 'or': 11,
        'what': 10, 'all': 10, 'take': 10, 'but': 10, "'s": 9, 'who': 9, 'there': 9, 'time': 9, 'go': 8, 'would': 8, 'new': 8,
        'by': 8, 'an': 8, 'like': 8, 'person': 7, 'about': 7, 'more': 7, 'me': 7, 'from': 7, 'his': 7, 'out': 6, 'call': 6,
        'enough': 6, 'now': 6, 'their': 6, 'should': 6, 'could': 6, 'also': 6, 'any': 6, 'come': 6, 'our': 6, 'find': 5, 'how': 5,
        'want': 5, 'think': 5, 'very': 5, 'one': 5, 'first': 5, 'try': 5, 'him': 5}
    for lemma,poses in poses_by_lemma.items():
        if lemmas[lemma]>=5:
            ambig_class[frozenset(poses)].add(lemma)

    print(cgels)
    #print(lemmas.most_common(70))
    for k,v in ambig_class.items():
        print({x for x in sorted(k)}, ': ', ' '.join(sorted(v)), sep='')
    for k,v in fxn_words.items():
        print(f'{k:>11}', ': ', ', '.join(sorted(v)), sep='')
    print(cats)
    print(fxns)

    # tags, cats, fxns formatted for LaTeX table
    nGAPs = cats['GAP']
    del cats['GAP']
    del fxns['(root)']
    for (p,pN),(c,cN),(f,fN) in zip_longest(cgels.most_common(), cats.most_common(), fxns.most_common(), fillvalue=('','')):
        p = p.replace("_",r"\_")
        c = c.replace("_",r"\_")
        f = f.replace("_",r"\_")
        print(rf'{pN:3} & {p:11} & {cN:4} & {c:20} & {fN:4} & {f} \\')
    print(nGAPs, r'& \textit{GAP}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('type', help='type of analysis', type=str)
    parser.add_argument('--file', help='file to analyse', type=str, default='all', required=False)
    args = parser.parse_args()

    files = [all_files[args.file]] if args.file != "all" else list(all_files.values())

    trees = []
    for file in files:
        with open(file, 'r') as f:
            for tree in cgel.trees(f):
                trees.append(tree)

    if args.type == 'overview':
        overview(trees)
    elif args.type == 'pos':
        analyse_pos(trees)

if __name__ == "__main__":
    main()