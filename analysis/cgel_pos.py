import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter, defaultdict
from math import log
from difflib import get_close_matches
from itertools import zip_longest

"""
Report stats on CGEL POSes only (without aligning to UD).
Also count phrasal categories and functions.
"""

def map_mult(s, olds, new):
    return new if any(o==s for o in olds) else s

with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
    ud_data = conllu.parse(f.read() + f2.read())

trees = []
with open('../datasets/twitter.cgel') as f, open('../datasets/ewt.cgel') as f2:
    a = ''.join([x for x in f.readlines() + f2.readlines() if x[0] in [' ', '(']])
    for tree in cgel.parse(a):
        trees.append(tree)
        #trees.append(conllu.parse(tree.to_conllu())[0])

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
        if not node.text:  # not a terminal
            if node.constituent in ('N','V','Adj','Adv','D','P','Coordinator','Int','N_pro','Sbr','V_aux'):
                # most of these are due to preprocessing errors. a couple are legitimate lexical coordinations
                if node.deprel!='Coordinate':
                    print('weird',node.deprel,node.constituent,cgel_tree.sentence())
                    continue
                cats[node.constituent+'@coord'] += 1
            else:
                cats[node.constituent] += 1

            if not node.deprel:
                assert node.head==-1
                fxns['(root)'] += 1
            else:
                fxns[node.deprel] += 1
            continue
        cgel_pos = node.constituent
        cgels[cgel_pos] += 1
        lemma = node.lemma
        lemmas[lemma] += 1
        poses_by_lemma[lemma].add(cgel_pos)
        if lemma in ('be',) and cgel_pos=='P':
            assert False,node
        if cgel_pos not in ('V','N','Adj','Adv','Int'):
            fxn_words[cgel_pos].add(lemma)

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
