import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter, defaultdict
from math import log
from difflib import get_close_matches
from itertools import zip_longest
from pprint import pprint

"""
Extract rules from CGEL trees.
"""

trees = []
with open('../datasets/twitter_cgel.txt') as f, open('../datasets/ewt_cgel.txt') as f2:
    a = ''.join([x for x in f.readlines() + f2.readlines() if x[0] in [' ', '(']])
    for tree in cgel.parse(a):
        trees.append(tree)
        #trees.append(conllu.parse(tree.to_conllu())[0])

fxn_words = {'D': set(), 'N_pro': set(), 'P': set(), 'Sdr': set(), 'Coordinator': set()}

rules = Counter()  # {(CAT, Fxn, Fxn2, Fxn3, ...): count}   [where CAT -> Fxn, Fxn2, Fxn3, ... is the rule]
cats_in_fxn = defaultdict(Counter)  # {Fxn^PARCAT: {CAT: count}}

# node properties: 'constituent' (POS or phrasal category), 'deprel' (grammatical function), 'head' (index), 'label' (coindexation variable), 'text' (terminals only)
for cgel_tree in trees:
    children = defaultdict(list)
    for node in cgel_tree.tokens.values():
        if node.head>-1:
            parent = cgel_tree.tokens[node.head]
            children[parent].append(node)

    for parent in children:
        #print(parent.constituent, '->', ' '.join(f'{child.deprel}:{child.constituent}' for child in children[parent]))
        ntlabel = parent.constituent
        #if parent.deprel=='Coordinate':
        #    ntlabel += '(c)'
        #if '+' in ntlabel and '(c)' not in ntlabel:
        #    assert False,cgel_tree.sentence()
        rule = (ntlabel,) + tuple(child.deprel for child in children[parent])
        #if rule==('NP','Subj'):
        #    assert False,cgel_tree.sentence()
        rules[rule] += 1
        for child in children[parent]:
            k = f'{child.deprel}^{parent.constituent}'  # e.g. Subj^Clause
            cats_in_fxn[k][child.constituent] += 1
            #if child.deprel=='Comp' and parent.constituent=='Nom' and len(rule)==2:
            #    assert False,(k,rule,cgel_tree.sentence())

print('PART 1: Counts of extracted rules (mother category + functions)')
print('  +h means more than one Head function; -h means no Head')
print()
for r,n in sorted(rules.items()):
    nHeads = sum(1 for fxn in r[1:] if fxn=='Head')
    flag = '+h' if nHeads>1 else '-h' if nHeads==0 else ''
    print(f'{n:4} {flag:2}', r[0], '->', ' '.join(r[1:]))
print()
print()
print('PART 2: Functions by mother and daughter categories')
print()
pprint({k: dict(v) for k,v in cats_in_fxn.items()}, width=100)
