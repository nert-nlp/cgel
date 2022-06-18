import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter
from math import log
from difflib import get_close_matches

with open('../datasets/twitter_ud.conllu') as f, open('../datasets/ewt_ud.conllu') as f2:
    ud_data = conllu.parse(f.read() + f2.read())

trees = []
with open('../datasets/twitter_cgel.txt') as f, open('../datasets/ewt_cgel.txt') as f2, open('cgel.conllu', 'w') as fout:
    a = ''.join([x for x in f.readlines() + f2.readlines() if x[0] in [' ', '(']])
    for tree in cgel.parse(a):
        trees.append(tree)
        fout.write(conllu.parse(tree.to_conllu())[0].serialize())

function, constituent = Counter(), Counter()
for tree in trees:
    for i, node in tree.tokens.items():
        function[node.deprel] += 1
        constituent[node.constituent] += 1

for i in constituent.most_common():
    print(i)